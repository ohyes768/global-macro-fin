"""ECB Statistical Data Warehouse API 服务模块"""
import pandas as pd
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional
from src.utils.logger import setup_logger
from src.utils.retry import async_retry

logger = setup_logger("ecb_service")

# ECB SDW API 端点（新域名）
ECB_API_BASE = "https://data-api.ecb.europa.eu/service/data"


class ECBService:
    """ECB 统计数据库服务类"""

    # 内部名称到 ECB 代码的映射
    GERMAN_BOND_CODES = {
        "eu_2y_ecb": "M.U2.EUR.4F.BB.U2_2Y.YLD",
        "eu_5y_ecb": "M.U2.EUR.4F.BB.U2_5Y.YLD",
        "eu_10y_ecb": "M.U2.EUR.4F.BB.U2_10Y.YLD",
    }

    def __init__(self):
        """初始化 ECB 服务"""
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/vnd.sdmx.data+json"})

    @async_retry(max_retries=3, delay=1.0)
    async def fetch_series(
        self, name: str, start_date: pd.Timestamp, end_date: pd.Timestamp
    ) -> pd.Series:
        """获取单个 ECB 数据系列

        Args:
            name: 数据系列名称（如 eu_2y_ecb）或 ECB 代码
            start_date: 起始日期
            end_date: 结束日期

        Returns:
            数据系列
        """
        # 映射名称到 ECB 代码
        series_key = self.GERMAN_BOND_CODES.get(name, name)

        logger.info(f"获取 ECB 数据: {name} -> {series_key}, 从 {start_date} 到 {end_date}")

        try:
            # ECB SDW API 使用的数据格式
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")

            # 构造请求 URL - 欧洲央行收益率数据在 FM 数据库中
            url = f"{ECB_API_BASE}/FM/{series_key}"

            params = {
                "startPeriod": start_str,
                "endPeriod": end_str,
                "detail": "full",  # 使用 full 获取时间轴信息
                "format": "jsondata",
            }

            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # 解析 SDW JSON 响应
            series_data = self._parse_sdmx_response(data)

            if series_data:
                logger.info(f"成功获取 {name} 数据，共 {len(series_data)} 条记录")
                return pd.Series(series_data, dtype="float64")
            else:
                logger.warning(f"{name} 返回数据为空")
                return pd.Series(dtype="float64")

        except Exception as e:
            logger.error(f"获取 {name} 数据失败: {str(e)}")
            return pd.Series(dtype="float64")

    def _parse_sdmx_response(self, data: dict) -> Dict[pd.Timestamp, float]:
        """解析 SDMX JSON 响应

        Args:
            data: SDMW JSON 响应数据

        Returns:
            日期到值的映射字典
        """
        result = {}

        try:
            # 提取时间轴信息
            time_periods = []
            if "structure" in data:
                structure = data["structure"]
                if "dimensions" in structure:
                    dims = structure["dimensions"]
                    if "observation" in dims:
                        obs_dims = dims["observation"]
                        # 找到时间维度
                        for dim in obs_dims:
                            if dim.get("id") == "TIME_PERIOD":
                                time_periods = dim.get("values", [])
                                break

            # 提取观测值数据
            data_sets = data.get("dataSets", [])
            if not data_sets:
                return result

            dataset = data_sets[0]
            series = dataset.get("series", {})

            # 获取第一个系列的数据
            observations = []
            if isinstance(series, dict) and series:
                first_series_key = list(series.keys())[0]
                observations = series[first_series_key].get("observations", {})

            # 将时间周期和观测值配对
            for idx, time_period in enumerate(time_periods):
                if idx >= len(observations):
                    break

                obs_key = str(idx)
                if obs_key not in observations:
                    continue

                obs_value = observations[obs_key]
                if not isinstance(obs_value, list) or len(obs_value) == 0:
                    continue

                value = obs_value[0]
                if value is None or not isinstance(value, (int, float)):
                    continue

                # 使用时间周期的 start 字段作为日期
                period_id = time_period.get("id", "")

                try:
                    # period_id 格式通常是 "YYYY-MM" 或 "YYYY"
                    if "-" in period_id:
                        date = pd.Timestamp(period_id + "-01")
                    else:
                        date = pd.Timestamp(period_id + "-01-01")

                    result[date] = float(value)
                except (ValueError, TypeError):
                    continue

        except Exception as e:
            logger.error(f"解析 SDMX 响应失败: {str(e)}")

        return result

    async def fetch_all_german_bonds(
        self, start_date: pd.Timestamp, end_date: pd.Timestamp
    ) -> Dict[str, pd.Series]:
        """获取所有德国国债收益率数据

        Args:
            start_date: 起始日期
            end_date: 结束日期

        Returns:
            包含所有德国国债数据的字典
        """
        result = {}

        for name, code in self.GERMAN_BOND_CODES.items():
            try:
                series = await self.fetch_series(name, start_date, end_date)
                result[name] = series
            except Exception as e:
                logger.error(f"获取 {name} ({code}) 数据时出错: {e}")
                # 创建空序列作为占位符
                result[name] = pd.Series(dtype="float64")

        return result


# 创建全局 ECB 服务实例
_ecb_service: Optional[ECBService] = None


def get_ecb_service() -> ECBService:
    """获取 ECB 服务单例

    Returns:
        ECB 服务实例
    """
    global _ecb_service
    if _ecb_service is None:
        _ecb_service = ECBService()
    return _ecb_service
