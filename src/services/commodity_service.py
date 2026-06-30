"""商品数据服务模块 — 阿里云 alirmcom2 comrms 批量接口（黄金/白银/原油/铜）

参考 dividend-select m120_service._get_realtime_prices_batch：
- 接口: GET /query/comrms?symbols=A,B,C,D（注意是 symbols 复数 + 逗号分隔）
- 认证: Authorization: APPCODE {appcode}
- 响应: {"Code":0, "Msg":"", "Obj":[{"C":代码, "P":实时价, "YC":昨日收盘, ...}, ...]}

策略：
- comrms 是实时行情接口（不带历史）
- commodity_service.fetch_all() 一次批量拿 4 个商品的最新价 + 昨日收盘
- 后端 routes update_commodities 把每天的价 append 到 commodities.csv（每天一行）
- 多次 append 累积成历史曲线（commodity tab 切换时间窗口看走势）
"""
import asyncio
from typing import Dict, Optional

import httpx

from src.config import get_settings
from src.utils.logger import setup_logger

logger = setup_logger("commodity_service")
settings = get_settings()


class AliyunCommodityClient:
    """阿里云 alirmcom2 商品批量客户端（基于 comrms 实时行情接口）"""

    API_PATH = "/query/comrms"

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

    async def fetch_realtime_batch(self, symbols: list[str]) -> Dict[str, dict]:
        """批量获取多个商品的实时行情

        Args:
            symbols: 商品代码列表（如 ["SGEAU9999", "SGEAG9999", "UKOIL", "USHG"]）

        Returns:
            {symbol: {"realtime": float | None, "close": float | None}}
            realtime = 当前实时价 (字段 P)，close = 昨日收盘 (字段 YC)
        """
        if not symbols:
            return {}
        if self._client is None:
            raise RuntimeError("AliyunCommodityClient must be used via 'async with'")

        # 一次调用拿所有商品的实时价 + 昨日收盘
        symbols_str = ",".join(symbols)
        params = {"symbols": symbols_str}
        url = f"{self._base}{self.API_PATH}"
        logger.info(f"aliyun comrms batch fetch {len(symbols)} symbols: {symbols_str}")
        resp = await self._client.get(url, params=params)
        resp.raise_for_status()
        payload = resp.json()

        if not isinstance(payload, dict):
            logger.error(f"aliyun comrms 返回非 dict: {type(payload).__name__}")
            return {}
        code_val = payload.get("Code")
        if code_val != 0:
            logger.error(f"aliyun comrms 返回错误: Code={code_val}, Msg={payload.get('Msg', '')}")
            return {}

        items = payload.get("Obj") or []
        logger.info(f"aliyun comrms 返回 Obj 数量: {len(items)}")

        out: Dict[str, dict] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            # comrms 返回的代码在 FS 字段（C 是空字符串），统一去前缀 + 大写
            code = item.get("FS", "")
            if not code:
                continue
            code_upper = code.upper()
            for prefix in ("SH", "SZ", "BJ"):
                if code_upper.startswith(prefix):
                    code = code_upper[len(prefix):]
                    break
            realtime = item.get("P")
            close = item.get("YC")
            out[code] = {
                "realtime": float(realtime) if realtime not in (None, "") else None,
                "close": float(close) if close not in (None, "") else None,
            }
        return out


class CommodityService:
    """商品数据服务 — 阿里云 alirmcom2 comrms 批量（黄金/白银/原油/铜）

    命名约定：
    - fetch_realtime() / fetch_all_realtime()：拿 4 个商品的当前价 + 昨日收盘（一次 comrms 调用）
    - 历史上累积的数据由后端 routes 在每次 update_commodities 时 append 到 commodities.csv
    """

    @staticmethod
    async def fetch_realtime(name: str) -> Optional[dict]:
        """获取单个商品的当前实时价 + 昨日收盘（单 symbol 批量调用）"""
        symbol = settings.commodity_symbols.get(name)
        if not symbol:
            logger.error(f"未知商品: {name}")
            return None
        if not settings.alirmcom_appcode:
            logger.error("ALIRMCOM_APPCODE 未配置")
            return None
        try:
            async with AliyunCommodityClient(
                settings.alirmcom_appcode, settings.alirmcom_base_url
            ) as client:
                batch = await client.fetch_realtime_batch([symbol])
                return batch.get(symbol)
        except Exception as e:
            logger.error(f"aliyun {name}({symbol}) 获取失败: {e}")
            return None

    @staticmethod
    async def fetch_all() -> Dict[str, dict]:
        """4 个商品一次性批量获取（单次 comrms 调用）

        Returns:
            dict: {gold: {realtime, close}, silver: ..., oil: ..., copper: ...}
        """
        if not settings.alirmcom_appcode:
            logger.error("ALIRMCOM_APPCODE 未配置")
            return {}
        names = ["gold", "silver", "oil", "copper"]
        symbols = [settings.commodity_symbols[n] for n in names if settings.commodity_symbols.get(n)]
        try:
            async with AliyunCommodityClient(
                settings.alirmcom_appcode, settings.alirmcom_base_url
            ) as client:
                batch = await client.fetch_realtime_batch(symbols)
        except Exception as e:
            logger.error(f"aliyun 批量获取失败: {e}")
            return {}

        out: Dict[str, dict] = {}
        for n in names:
            sym = settings.commodity_symbols.get(n)
            if sym and sym in batch:
                out[n] = batch[sym]
            else:
                out[n] = {"realtime": None, "close": None}
        return out


# 创建全局商品服务实例
_commodity_service: Optional[CommodityService] = None


def get_commodity_service() -> CommodityService:
    """获取商品服务单例"""
    global _commodity_service
    if _commodity_service is None:
        _commodity_service = CommodityService()
    return _commodity_service