"""股指数据服务模块 — 阿里云 alirmcom2 comkm K线接口（5 个全球股指）

参考 dividend-select calculator.py 的 comkm 翻页拉取：
- 接口: GET /query/comkm?period=D&pidx=1&psize=500&symbol=HKHSI&withlast=0
- 认证: Authorization: APPCODE {appcode}
- 响应: {"Code":0, "Msg":"", "Obj":[{"C":close, "O":open, "H":high, "L":low,
                                     "V":volume, "A":amount, "D":"YYYY-MM-DD 00:00:00",
                                     "Tick":unix_ts}, ...]}

策略：
- comkm 是历史 K 线接口（带翻页），5 个全球股指（恒生/上证/标普500/纳指/道指）
- 每个 symbol 单独翻页拉取（comkm 不支持批量 symbols=...，只能 pidx 翻页）
- 5 个 symbol 用 asyncio.gather 并发，错误隔离（一个失败不影响其他）
- 返回按 date 升序的 Series
- 后端 routes 在 fetch/indices/history 时全量写入 indices.csv，update/indices 时增量追加
"""
import asyncio
from datetime import date
from typing import Dict, List, Optional

import httpx
import pandas as pd

from src.config import get_settings
from src.utils.logger import setup_logger

logger = setup_logger("index_service")
settings = get_settings()


class AliyunIndexClient:
    """阿里云 alirmcom2 股指客户端（基于 comkm 历史 K线接口）

    comkm 不支持批量 symbols，所以每个 symbol 单独拉取+翻页
    """

    API_PATH = "/query/comkm"
    PAGE_SIZE = 500
    MAX_PAGES = 20  # 20 页 × 500 条 ≈ 27 年日线，足够 + 兜底防无限循环

    def __init__(self, appcode: str, base_url: str):
        self._headers = {"Authorization": f"APPCODE {appcode}"}
        self._base = base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "AliyunIndexClient":
        self._client = httpx.AsyncClient(headers=self._headers, timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def fetch_klines(self, symbol: str) -> List[dict]:
        """拉取单个 symbol 全部日 K 线（翻页累加，返回升序）

        Args:
            symbol: 指数代码（如 "HKHSI"/"SPX"/"SH000001"）

        Returns:
            [{"date": Timestamp, "close": float}, ...] 升序排列
            失败时返回已拉到的部分（不抛异常）
        """
        if self._client is None:
            raise RuntimeError("AliyunIndexClient must be used via 'async with'")

        all_records: List[dict] = []
        pidx = 1
        while pidx <= self.MAX_PAGES:
            params = (
                f"period=D&pidx={pidx}&psize={self.PAGE_SIZE}"
                f"&symbol={symbol}&withlast=0"
            )
            url = f"{self._base}{self.API_PATH}?{params}"
            try:
                resp = await self._client.get(url)
                resp.raise_for_status()
            except Exception as e:
                logger.error(f"aliyun comkm {symbol} pidx={pidx} HTTP 失败: {e}")
                return all_records  # 返回已拉到的部分

            try:
                payload = resp.json()
            except Exception as e:
                logger.error(f"aliyun comkm {symbol} pidx={pidx} JSON 解析失败: {e}")
                return all_records

            if not isinstance(payload, dict):
                logger.error(f"aliyun comkm {symbol} pidx={pidx} 返回非 dict: {type(payload).__name__}")
                return all_records
            code_val = payload.get("Code")
            if code_val != 0:
                logger.error(
                    f"aliyun comkm {symbol} pidx={pidx} 返回错误: "
                    f"Code={code_val}, Msg={payload.get('Msg', '')}"
                )
                return all_records

            klines = payload.get("Obj") or []
            for item in klines:
                if not isinstance(item, dict):
                    continue
                d_str = item.get("D")
                c_val = item.get("C")
                if not d_str or c_val in (None, ""):
                    continue
                # D 字段格式 "2026-04-13 00:00:00" 取前 10 字符
                try:
                    all_records.append({
                        "date": pd.Timestamp(d_str[:10]),
                        "close": float(c_val),
                    })
                except (ValueError, TypeError):
                    continue

            logger.info(f"aliyun comkm {symbol} pidx={pidx} 返回 {len(klines)} 条，累计 {len(all_records)} 条")

            if len(klines) < self.PAGE_SIZE:
                # 数据不足一页，说明翻页到头
                break
            pidx += 1

        if pidx > self.MAX_PAGES:
            logger.warning(f"aliyun comkm {symbol} 翻页超过 {self.MAX_PAGES} 次，主动停止")

        # 阿里云返回是倒序（最新在前），翻为升序
        all_records.sort(key=lambda r: r["date"])
        return all_records


class IndexService:
    """5 个全球股指并发拉取服务

    comkm 不支持批量，所以用 asyncio.gather 让 5 个 client 并发拉取（网络 I/O 等待重叠）
    """

    @staticmethod
    async def fetch_all(
        start_date: date, end_date: date
    ) -> Dict[str, pd.Series]:
        """并发拉 5 个指数日 K 线，按日期范围过滤

        Args:
            start_date: 起始日期（含）
            end_date: 结束日期（含）

        Returns:
            {HKHSI: Series, SH000001: Series, SPX: Series, IXIC: Series, DJI: Series}
            Series.index 是 date（Timestamp），values 是 close（float）
            失败的 symbol 对应空 Series（不抛异常）
        """
        if not settings.alirmcom_appcode:
            logger.error("ALIRMCOM_APPCODE 未配置")
            return {}

        names = list(settings.index_symbols.keys())

        async def _fetch_one(name: str) -> tuple[str, pd.Series]:
            sym = settings.index_symbols[name]
            try:
                async with AliyunIndexClient(
                    settings.alirmcom_appcode, settings.alirmcom_base_url
                ) as client:
                    records = await client.fetch_klines(sym)
            except Exception as e:
                logger.error(f"aliyun 拉取 {name}({sym}) 失败: {e}")
                return name, pd.Series(dtype="float64")

            if not records:
                return name, pd.Series(dtype="float64")

            df = pd.DataFrame(records).set_index("date").sort_index()
            # 去重（同一日期多次拉取保留最后一次）
            df = df[~df.index.duplicated(keep="last")]
            # 按日期范围过滤
            mask = (df.index >= pd.Timestamp(start_date)) & (df.index <= pd.Timestamp(end_date))
            return name, df.loc[mask, "close"]

        results = await asyncio.gather(*[_fetch_one(n) for n in names])
        logger.info(f"5 个指数并发拉取完成: {[(n, len(s)) for n, s in results]}")
        return {name: series for name, series in results}


# 全局单例
_index_service: Optional[IndexService] = None


def get_index_service() -> IndexService:
    """获取股指服务单例"""
    global _index_service
    if _index_service is None:
        _index_service = IndexService()
    return _index_service
