"""FRED API 服务模块"""
import pandas as pd
from fredapi import Fred
from datetime import datetime, timedelta
from typing import Dict, Optional
from src.config import get_settings
from src.utils.logger import setup_logger
from src.utils.retry import async_retry

logger = setup_logger("fred_service")
settings = get_settings()


class FredService:
    """FRED API 服务类"""

    def __init__(self):
        """初始化 FRED 服务"""
        self.fred = Fred(api_key=settings.fred_api_key)
        self.fred_codes = settings.fred_codes

    @async_retry(max_retries=3, delay=1.0)
    async def fetch_series(
        self, code: str, start_date: pd.Timestamp, end_date: pd.Timestamp
    ) -> pd.Series:
        """获取单个 FRED 数据系列

        Args:
            code: FRED 数据代码
            start_date: 起始日期
            end_date: 结束日期

        Returns:
            数据系列
        """
        # OECD 数据（德国、日本）是月度数据，自动扩展查询范围到 365 天
        oecd_codes = {"IRLTLT01DEM156N", "IRLTLT01JPM156N"}
        if code in oecd_codes:
            start_date = (end_date - pd.Timedelta(days=365)).normalize()
            logger.info(f"{code} 是 OECD 月度数据，自动扩展查询范围: {start_date} 到 {end_date}")

        logger.info(f"获取 FRED 数据: {code}, 从 {start_date} 到 {end_date}")

        try:
            series = self.fred.get_series(
                code, observation_start=start_date, observation_end=end_date
            )
            logger.info(f"成功获取 {code} 数据，共 {len(series)} 条记录")
            return series
        except Exception as e:
            logger.error(f"获取 {code} 数据失败: {str(e)}")
            raise

    async def fetch_all_treasuries(
        self, start_date: pd.Timestamp, end_date: pd.Timestamp
    ) -> Dict[str, pd.Series]:
        """获取所有国债数据

        Args:
            start_date: 起始日期
            end_date: 结束日期

        Returns:
            包含所有国债数据的字典
        """
        result = {}

        # OECD 数据（德国、日本）是月度数据，需要更长的查询范围
        oecd_codes = {"eu_10y", "jp_10y"}

        for name, code in self.fred_codes.items():
            try:
                # 对 OECD 数据使用更长的日期范围（365天）
                if name in oecd_codes:
                    oecd_start = (end_date - pd.Timedelta(days=365)).normalize()
                    logger.info(f"{name} 是月度数据，扩大查询范围: {oecd_start} 到 {end_date}")
                    series = await self.fetch_series(code, oecd_start, end_date)
                else:
                    series = await self.fetch_series(code, start_date, end_date)
                result[name] = series
            except Exception as e:
                logger.error(f"获取 {name} ({code}) 数据时出错: {e}")
                # 创建空序列作为占位符
                result[name] = pd.Series(dtype="float64")

        return result

    async def fetch_latest_data(self) -> Dict[str, pd.Series]:
        """获取最新的数据点

        Returns:
            包含最新数据的字典
        """
        # 获取最近7天的数据（确保有数据）
        end = pd.Timestamp.now().normalize()
        start = (end - pd.Timedelta(days=7)).normalize()

        data = await self.fetch_all_treasuries(start, end)

        # 过滤出最新的非空数据点
        latest = {}
        for name, series in data.items():
            if not series.empty:
                # 获取最后一个非空值
                last_valid = series.last_valid_index()
                if last_valid is not None:
                    latest[name] = pd.Series(
                        {last_valid: series[last_valid]}, dtype="float64"
                    )

        return latest


# 创建全局 FRED 服务实例
_fred_service: Optional[FredService] = None


def get_fred_service() -> FredService:
    """获取 FRED 服务单例

    Returns:
        FRED 服务实例
    """
    global _fred_service
    if _fred_service is None:
        _fred_service = FredService()
    return _fred_service
