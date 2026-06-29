"""商品数据服务模块 — 阿里云市场 alirmcom2 API（黄金/白银/原油/铜）"""
import asyncio
from typing import Dict, Optional

import httpx
import pandas as pd

from src.config import get_settings
from src.utils.logger import setup_logger

logger = setup_logger("commodity_service")
settings = get_settings()


class AliyunCommodityClient:
    """阿里云市场 alirmcom2 商品客户端

    真实路径 / params / 响应字段在 alirmcom2 文档不可访问时按通用阿里云市场 API 模式：
      - URL: {base_url}/{symbol}
      - Header: Authorization: APPCODE {appcode}
      - 响应: JSON 中 records / data / list 字段，按 date+price 解析
    首次接入时如发现真实接口形态不符，只调整本类内部实现，
    不影响上层 CommodityService 接口。
    """

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
        """获取单个商品历史 K 线（阿里云 alirmcom2）

        Args:
            symbol: 商品代码（SGEAU9999 / SGEAG9999 / UKOIL / USHG）
            start_date: 起始日期
            end_date: 结束日期

        Returns:
            价格 Series（按日期索引），name=symbol
        """
        if self._client is None:
            raise RuntimeError("AliyunCommodityClient must be used via 'async with'")

        url = f"{self._base}/{symbol}"
        params = {
            "begin": start_date.strftime("%Y%m%d"),
            "end": end_date.strftime("%Y%m%d"),
        }
        logger.info(f"aliyun fetch {symbol}: {params}")
        resp = await self._client.get(url, params=params)
        resp.raise_for_status()
        payload = resp.json()

        # 响应解析按真实格式调整 —— 通用兜底：找 records / data / list 字段，按 date/price 列名解析
        records = (
            payload.get("records")
            or payload.get("data")
            or payload.get("list")
            or payload.get("result")
            or []
        )
        if isinstance(records, dict):
            # 兼容 {"data": [{"date":..., "price":...}]} 或 {"data": {"items": [...]}}
            records = records.get("items") or records.get("list") or []

        rows = []
        for r in records:
            if not isinstance(r, dict):
                continue
            d = r.get("date") or r.get("time") or r.get("day") or r.get("datetime")
            p = r.get("price") or r.get("close") or r.get("value") or r.get("last")
            if d is None or p is None:
                continue
            try:
                rows.append({"date": pd.to_datetime(d), "price": float(p)})
            except (ValueError, TypeError):
                continue

        if not rows:
            logger.warning(f"aliyun {symbol} 返回无有效数据 (response keys: {list(payload.keys()) if isinstance(payload, dict) else type(payload).__name__})")
            return pd.Series(dtype="float64", name=symbol)

        df = pd.DataFrame(rows).set_index("date").sort_index()
        # 过滤日期范围（防止接口返回范围外数据）
        df = df[(df.index >= start_date) & (df.index <= end_date)]
        return df["price"].rename(symbol)


class CommodityService:
    """商品数据服务 — 统一走阿里云市场 API（黄金/白银/原油/铜）"""

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