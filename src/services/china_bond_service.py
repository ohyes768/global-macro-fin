"""中国国债服务模块"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional
import akshare as ak
from src.config import get_settings
from src.utils.logger import setup_logger

logger = setup_logger("china_bond_service")
settings = get_settings()


class ChinaBondService:
    """中国国债服务类 - 使用 AKShare 获取中国国债收益率数据"""

    def __init__(self):
        """初始化中国国债服务"""
        self.start_date = settings.china_bond_start_date

    def fetch_china_bond_yield(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """获取中国国债收益率曲线数据

        Args:
            start_date: 起始日期 (YYYY-MM-DD)，默认为配置中的起始日期
            end_date: 结束日期 (YYYY-MM-DD)，默认为今天

        Returns:
            中国国债收益率数据 DataFrame
        """
        try:
            logger.info(f"获取中国国债收益率数据: {start_date or self.start_date} 到 {end_date or '今天'}")

            # AKShare 接口：中国国债收益率曲线
            df = ak.bond_china_yield()

            # 转换日期列
            date_col = df.columns[0]
            df["date"] = pd.to_datetime(df[date_col])
            df = df.set_index("date")

            # 筛选日期范围
            start_dt = pd.to_datetime(start_date) if start_date else pd.to_datetime(self.start_date)
            end_dt = pd.to_datetime(end_date) if end_date else pd.Timestamp.now().normalize()

            df = df[(df.index >= start_dt) & (df.index <= end_dt)]

            logger.info(f"成功获取中国国债收益率数据，共 {len(df)} 条记录")
            return df

        except Exception as e:
            logger.error(f"获取中国国债收益率数据失败: {str(e)}")
            raise

    def fetch_10y_yield(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> pd.Series:
        """获取10年期中国国债收益率

        Args:
            start_date: 起始日期 (YYYY-MM-DD)，默认为配置中的起始日期
            end_date: 结束日期 (YYYY-MM-DD)，默认为今天

        Returns:
            10年期中国国债收益率 Series
        """
        df = self.fetch_china_bond_yield(start_date, end_date)

        # 查找10年期国债收益率列
        # AKShare 返回的列名通常是 "10年" 或类似的中文列名
        col_10y = None
        possible_names = ["10年", "10年国债", "中国国债10年", "10Y"]

        for col in df.columns:
            col_str = str(col).lower()
            if any(name.lower() in col_str for name in possible_names):
                col_10y = col
                break

        if col_10y is None:
            # 默认使用第二列（通常是中国国债收益率曲线的10年期）
            # 第一列通常是日期
            if len(df.columns) > 1:
                col_10y = df.columns[1]
                logger.info(f"未找到10年期特定列，使用默认列: {col_10y}")
            else:
                raise Exception("中国国债收益率数据列不足")

        logger.info(f"10年期中国国债列名: {col_10y}")

        # 返回10年期数据
        result = df[col_10y].dropna()
        logger.info(f"10年期中国国债收益率数据: {len(result)} 条记录")

        return result

    def get_latest_10y_yield(self) -> Optional[Dict]:
        """获取最新的10年期中国国债收益率

        Returns:
            包含最新收益率和日期的字典
        """
        try:
            series = self.fetch_10y_yield()

            if series.empty:
                return None

            last_idx = series.last_valid_index()
            if last_idx is None:
                return None

            return {
                "date": last_idx.date(),
                "value": float(series[last_idx]) if pd.notna(series[last_idx]) else None
            }

        except Exception as e:
            logger.error(f"获取最新10年期中国国债收益率失败: {str(e)}")
            return None


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
