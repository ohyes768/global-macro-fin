"""中国国债服务模块 - 使用 AKShare bond_zh_us_rate 接口"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional
import akshare as ak
from src.config import get_settings
from src.utils.logger import setup_logger

logger = setup_logger("china_bond_service")
settings = get_settings()


class ChinaBondService:
    """中国国债服务类 - 使用 AKShare bond_zh_us_rate 接口获取中美国债收益率"""

    def __init__(self):
        """初始化中国国债服务"""
        self.start_date = settings.china_bond_start_date

    def fetch_china_bond_yield(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """获取中国国债收益率数据（10 年期 + 10-2 利差）

        Args:
            start_date: 起始日期 (YYYY-MM-DD)，默认为配置中的起始日期
            end_date: 结束日期 (YYYY-MM-DD)，默认为今天

        Returns:
            DataFrame 含 "中国国债收益率10年" 和 "中国国债收益率10年-2年" 两列，index 为 datetime
        """
        try:
            logger.info(f"获取中国国债收益率数据: {start_date or self.start_date} 到 {end_date or '今天'}")

            # AKShare 接口：中美国债收益率（9287 条 × 13 列，1990-12-19 ~ 今天，日度）
            df = ak.bond_zh_us_rate()

            # 按列名精确选取（避免依赖列顺序；含兜底逻辑防 ak 接口列名变化）
            target_cols = ["中国国债收益率10年", "中国国债收益率10年-2年"]
            available = [c for c in target_cols if c in df.columns]
            if not available:
                # 兜底：扫描含 "10年" 的列（兼容 ak 接口升级导致列名变化）
                available = [c for c in df.columns if "10年" in str(c)]
                if not available:
                    raise Exception(
                        f"ak.bond_zh_us_rate 列名变更，未找到 10y 相关列。当前列: {df.columns.tolist()}"
                    )
                logger.warning(f"ak 列名偏离预期，使用兜底匹配: {available}")

            df = df[["日期"] + available].copy()
            df["date"] = pd.to_datetime(df["日期"])
            df = df.set_index("date")[available]

            # 筛选日期范围
            start_dt = pd.to_datetime(start_date) if start_date else pd.to_datetime(self.start_date)
            end_dt = pd.to_datetime(end_date) if end_date else pd.Timestamp.now().normalize()

            df = df[(df.index >= start_dt) & (df.index <= end_dt)]

            logger.info(f"成功获取中国国债收益率数据，共 {len(df)} 条记录，列: {available}")
            return df

        except Exception as e:
            logger.error(f"获取中国国债收益率数据失败: {str(e)}")
            raise


# 创建全局中国国债服务实例
_china_bond_service: Optional[ChinaBondService] = None


def get_china_bond_service() -> ChinaBondService:
    """获取中国国债服务单例

    Returns:
        中国国债服务实例
    """
    global _china_bond_service
    if _china_bond_service is None:
        _china_bond_service = ChinaBondService()
    return _china_bond_service