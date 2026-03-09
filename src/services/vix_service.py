"""VIX恐慌指数服务模块"""
import pandas as pd
from src.config import get_settings
from src.utils.logger import setup_logger

logger = setup_logger("vix_service")
settings = get_settings()


class VIXService:
    """VIX恐慌指数服务类"""

    def __init__(self):
        """初始化VIX服务"""
        self.vix_code = settings.fred_codes.get("vix", "VIXCLS")

    def convert_timezone(self, data: pd.Series) -> pd.Series:
        """转换时区（ET → UTC）

        Args:
            data: VIX数据系列

        Returns:
            转换时区后的数据系列
        """
        try:
            # 如果数据没有时区信息，先设置为ET时区，然后转换为UTC
            if data.index.tz is None:
                data.index = data.index.tz_localize('US/Eastern')
            data.index = data.index.tz_convert('UTC')
            logger.info("VIX数据时区转换成功（ET → UTC）")
            return data
        except Exception as e:
            logger.warning(f"时区转换失败，使用原始时区: {str(e)}")
            return data

    def validate_data(self, data: pd.Series) -> pd.Series:
        """验证和清洗VIX数据

        Args:
            data: VIX数据系列

        Returns:
            清洗后的数据系列
        """
        # 移除空值
        data = data.dropna()

        # 验证VIX值的合理性（通常在0-100之间）
        if not data.empty:
            # 标记异常值（VIX > 100 或 VIX < 0）
            abnormal = (data > 100) | (data < 0)
            if abnormal.any():
                abnormal_count = abnormal.sum()
                logger.warning(
                    f"发现 {abnormal_count} 个异常VIX值，已移除"
                )
                data = data[~abnormal]

        # 前向填充非交易日数据
        data = data.ffill()

        logger.info(f"VIX数据验证完成，有效记录数: {len(data)}")
        return data

    def normalize_data(self, data: pd.Series) -> pd.Series:
        """标准化VIX数据格式

        Args:
            data: VIX数据系列

        Returns:
            标准化后的数据系列
        """
        # 确保索引为日期类型
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)

        # 移除时区信息用于CSV存储（统一使用日期格式）
        if data.index.tz is not None:
            data.index = data.index.tz_convert(None)

        # 按日期排序
        data = data.sort_index()

        # 重命名系列为Close_VIX
        data.name = "Close_VIX"

        logger.info("VIX数据格式标准化完成")
        return data


# 创建全局VIX服务实例
_vix_service: VIXService = None


def get_vix_service() -> VIXService:
    """获取VIX服务单例

    Returns:
        VIX服务实例
    """
    global _vix_service
    if _vix_service is None:
        _vix_service = VIXService()
    return _vix_service