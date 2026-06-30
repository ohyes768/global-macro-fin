"""HIBOR 服务模块 - 调用香港金管局 HKMA 公开 API 获取隔夜拆息数据"""
import pandas as pd
import requests
from typing import Dict, Optional
from src.utils.logger import setup_logger
from src.utils.retry import async_retry

logger = setup_logger("hibor_service")

# HKMA 公开市场数据 API：每日银行间流动资金统计
HKMA_API_URL = (
    "https://api.hkma.gov.hk/public/market-data-and-statistics/"
    "daily-monetary-statistics/daily-figures-interbank-liquidity"
)


class HIBORService:
    """HIBOR 隔夜拆息服务类

    数据源：HKMA 公开 API
    字段：hibor_overnight（隔夜拆息，年化百分比）
    频率：每个香港交易日
    """

    def __init__(self):
        """初始化 HIBOR 服务"""
        self.session = requests.Session()

    @async_retry(max_retries=3, delay=1.0)
    async def fetch_series(
        self, start_date: pd.Timestamp, end_date: pd.Timestamp
    ) -> pd.Series:
        """获取 HIBOR 隔夜数据

        Args:
            start_date: 起始日期
            end_date: 结束日期

        Returns:
            日期索引的 Series（值为 hibor_overnight 百分比）
        """
        params = {
            "from": start_date.strftime("%Y%m%d"),
            "to": end_date.strftime("%Y%m%d"),
        }

        logger.info(f"获取 HIBOR 数据: 从 {start_date} 到 {end_date}")

        try:
            response = self.session.get(HKMA_API_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            records = data.get("result", {}).get("records", [])
            if not records:
                logger.warning("HIBOR 返回数据为空")
                return pd.Series(dtype="float64")

            df = pd.DataFrame(records)
            if "end_of_date" not in df.columns or "hibor_overnight" not in df.columns:
                logger.warning(
                    f"HIBOR 响应缺少必要字段。当前列: {df.columns.tolist()}"
                )
                return pd.Series(dtype="float64")

            df = df[["end_of_date", "hibor_overnight"]].copy()
            df["end_of_date"] = pd.to_datetime(df["end_of_date"])
            df["hibor_overnight"] = pd.to_numeric(df["hibor_overnight"], errors="coerce")
            df = df.dropna(subset=["hibor_overnight"])

            df = df.set_index("end_of_date").sort_index()
            series = df["hibor_overnight"]
            series.name = "hibor_overnight"

            logger.info(f"成功获取 HIBOR 数据，共 {len(series)} 条记录")
            return series

        except Exception as e:
            logger.error(f"获取 HIBOR 数据失败: {str(e)}")
            raise


# 创建全局 HIBOR 服务实例
_hibor_service: Optional[HIBORService] = None


def get_hibor_service() -> HIBORService:
    """获取 HIBOR 服务单例

    Returns:
        HIBOR 服务实例
    """
    global _hibor_service
    if _hibor_service is None:
        _hibor_service = HIBORService()
    return _hibor_service