"""商品数据服务模块 — 阿里云 alirmcom2 API（黄金/白银/原油/铜）

参考 dividend-select 的真实实现（calculator.py / m120_service.py）：
- 接口域名: http://alirmcom2.market.alicloudapi.com（注意是 http 不是 https）
- 历史 K 线: /query/comkm（支持翻页；商品需要历史曲线，用这个）
- 批量实时行情: /query/comrms（只返回最新价；不适合画历史曲线）
- 认证: Authorization: APPCODE {appcode}
- 响应: {"Code": 0, "Msg": "", "Obj": [{"C": 收盘, "D": "YYYY-MM-DD HH:MM:SS", ...}]}
- 翻页参数: period=D（日线）/ pidx=页码 / psize=每页条数 / withlast=0
"""
import asyncio
from typing import Dict, Optional

import httpx
import pandas as pd

from src.config import get_settings
from src.utils.logger import setup_logger

logger = setup_logger("commodity_service")
settings = get_settings()


class AliyunCommodityClient:
    """阿里云 alirmcom2 商品 K 线客户端（基于 comkm 接口，参考 dividend-select）"""

    API_PATH = "/query/comkm"

    def __init__(self, appcode: str, base_url: str):
        self._headers = {"Authorization": f"APPCODE {appcode}"}
        self._base = base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "AliyunCommodityClient":
        self._client = httpx.AsyncClient(headers=self._headers, timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def fetch_history(
        self,
        symbol: str,
        start_date: pd.Timestamp,
        end_date: pd.Timestamp,
    ) -> pd.Series:
        """获取单个商品历史 K 线（阿里云 alirmcom2 comkm 接口）

        翻页策略：从 pidx=1 开始按 psize=500 拉，直到数据日期早于 start_date。

        Args:
            symbol: 商品代码（SGEAU9999 / SGEAG9999 / UKOIL / USHG）
            start_date: 起始日期
            end_date: 结束日期（实际接口按 pidx 翻页，不由 end_date 控制）

        Returns:
            价格 Series（按日期索引），name=symbol
        """
        if self._client is None:
            raise RuntimeError("AliyunCommodityClient must be used via 'async with'")

        all_rows: list[dict] = []
        pidx = 1
        while True:
            params = {
                "period": "D",
                "pidx": pidx,
                "psize": 500,
                "symbol": symbol,
                "withlast": 0,
            }
            url = f"{self._base}{self.API_PATH}"
            logger.info(f"aliyun fetch {symbol} page {pidx}")
            resp = await self._client.get(url, params=params)
            resp.raise_for_status()
            payload = resp.json()

            if not isinstance(payload, dict):
                logger.error(f"aliyun {symbol} 返回非 dict: {type(payload).__name__}")
                break
            code_val = payload.get("Code")
            if code_val != 0:
                logger.error(f"aliyun {symbol} 返回错误: Code={code_val}, Msg={payload.get('Msg', '')}")
                break

            klines = payload.get("Obj") or []
            if not klines:
                break

            earliest_reached = False
            for item in klines:
                if not isinstance(item, dict):
                    continue
                date_str = item.get("D", "")
                close_val = item.get("C")
                if not date_str or close_val is None:
                    continue
                try:
                    ts = pd.to_datetime(date_str)
                    if ts < start_date:
                        earliest_reached = True
                        break
                    if ts <= end_date:
                        all_rows.append({"date": ts, "price": float(close_val)})
                except (ValueError, TypeError):
                    continue

            # 数据按日期倒序返回；本批已读到 start_date 之前就停
            if earliest_reached:
                break
            if len(klines) < 500:
                break  # 最后一页
            pidx += 1
            if pidx > 50:  # 防御性上限：500 × 50 = 25000 条
                logger.warning(f"aliyun {symbol} 翻页超过 50 次，强制停止")
                break

        if not all_rows:
            logger.warning(f"aliyun {symbol} 无有效数据")
            return pd.Series(dtype="float64", name=symbol)

        df = pd.DataFrame(all_rows).set_index("date").sort_index()
        return df["price"].rename(symbol)


class CommodityService:
    """商品数据服务 — 统一走阿里云 alirmcom2 comkm（黄金/白银/原油/铜）"""

    @staticmethod
    async def fetch_history(
        name: str, start_date: pd.Timestamp, end_date: pd.Timestamp
    ) -> pd.Series:
        """获取单个商品历史数据（gold / silver / oil / copper）"""
        symbol = settings.commodity_symbols.get(name)
        if not symbol:
            logger.error(f"未知商品: {name}（应在 commodity_symbols 中）")
            return pd.Series(dtype="float64", name=name)
        if not settings.alirmcom_appcode:
            logger.error("ALIRMCOM_APPCODE 未配置，无法调用阿里云商品 API")
            return pd.Series(dtype="float64", name=name)
        try:
            async with AliyunCommodityClient(
                settings.alirmcom_appcode, settings.alirmcom_base_url
            ) as client:
                return await client.fetch_history(symbol, start_date, end_date)
        except Exception as e:
            logger.error(f"aliyun {name}({symbol}) 获取失败: {e}")
            return pd.Series(dtype="float64", name=name)

    @staticmethod
    async def fetch_all(
        start_date: pd.Timestamp, end_date: pd.Timestamp
    ) -> Dict[str, pd.Series]:
        """4 个商品并行 fetch（asyncio.gather，单商品失败不拖垮其他）

        Returns:
            dict: {gold, silver, oil, copper} -> pd.Series
        """
        names = ["gold", "silver", "oil", "copper"]
        tasks = [CommodityService.fetch_history(n, start_date, end_date) for n in names]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        out: Dict[str, pd.Series] = {}
        for n, r in zip(names, results):
            if isinstance(r, Exception):
                logger.error(f"gather {n} 异常: {r}")
                out[n] = pd.Series(dtype="float64", name=n)
            else:
                out[n] = r
        return out


# 创建全局商品服务实例
_commodity_service: Optional[CommodityService] = None


def get_commodity_service() -> CommodityService:
    """获取商品服务单例"""
    global _commodity_service
    if _commodity_service is None:
        _commodity_service = CommodityService()
    return _commodity_service