"""资金流向服务模块"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import akshare as ak
from src.config import get_settings
from src.utils.logger import setup_logger

logger = setup_logger("fund_flow_service")
settings = get_settings()


class FundFlowService:
    """资金流向服务类 - 使用 AKShare 获取沪深港通资金流向数据"""

    def __init__(self):
        """初始化资金流向服务"""
        self.start_date = settings.fund_flow_start_date

    def fetch_all_fund_flow(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> Dict[str, pd.DataFrame]:
        """获取所有资金流向数据（北向和南向）

        Args:
            start_date: 起始日期 (YYYY-MM-DD)，默认为配置中的起始日期
            end_date: 结束日期 (YYYY-MM-DD)，默认为今天

        Returns:
            包含北向和南向资金流向数据的字典
        """
        try:
            logger.info(f"获取资金流向历史数据: {start_date or self.start_date} 到 {end_date or '今天'}")

            # AKShare 接口：市场资金流向
            df = ak.stock_market_fund_flow()

            # 使用列索引来访问（避免编码问题）
            # 列索引：0=日期, 1=上证净流入, 2=上证涨幅, 3=深证净流入, 4=深证涨幅, 5=沪深港通净流入, 6=沪深港通涨幅
            # 7=北向净流入, 8=北向涨幅, 9=南向净流入, 10=南向涨幅, 11=中证全指, 12=中证全指涨幅, 13=上证50, 14=上证50涨幅
            if len(df.columns) >= 11:
                # 转换日期列
                date_col = df.columns[0]
                df["date"] = pd.to_datetime(df[date_col])
                df = df.set_index("date")

                # 筛选日期范围
                start_dt = pd.to_datetime(start_date) if start_date else pd.to_datetime(self.start_date)
                end_dt = pd.to_datetime(end_date) if end_date else pd.Timestamp.now().normalize()

                df = df[(df.index >= start_dt) & (df.index <= end_dt)]

                # 构建北向和南向资金数据
                result = {}

                # 北向资金数据（列索引：7=净流入, 8=涨幅）
                # 数据单位是元，需要转换为亿元（除以 1 亿）
                north_data = pd.DataFrame({
                    "net_flow": df.iloc[:, 7] / 1e8,  # 转换为亿元
                    "buy": None,  # 该接口没有买入/卖出额
                    "sell": None
                })
                north_data.index = df.index
                result["north"] = north_data

                # 南向资金数据（列索引：9=净流入, 10=涨幅）
                # 数据单位是元，需要转换为亿元（除以 1 亿）
                south_data = pd.DataFrame({
                    "net_flow": df.iloc[:, 9] / 1e8,  # 转换为亿元
                    "buy": None,
                    "sell": None
                })
                south_data.index = df.index
                result["south"] = south_data

                logger.info(f"成功获取资金流向数据，北向 {len(result['north'])} 条，南向 {len(result['south'])} 条记录")
                return result
            else:
                logger.error(f"返回的列数不足: {len(df.columns)}")
                raise Exception(f"返回的列数不足: {len(df.columns)}")

        except Exception as e:
            logger.error(f"获取资金流向数据失败: {str(e)}")
            raise

    def fetch_latest_fund_flow(self) -> Dict[str, pd.DataFrame]:
        """获取最新的资金流向数据点

        Returns:
            包含最新北向和南向资金流向数据的字典
        """
        # 获取最近7天的数据（确保有数据）
        end = pd.Timestamp.now().normalize()
        start = (end - pd.Timedelta(days=7)).normalize()

        data = self.fetch_all_fund_flow(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

        # 过滤出最新的非空数据点
        latest = {}
        for direction, df in data.items():
            if not df.empty:
                last_idx = df.last_valid_index()
                if last_idx is not None:
                    latest[direction] = df.loc[[last_idx]]

        return latest

    def calculate_cumulative_flow(
        self, direction: str = "north"
    ) -> Dict[str, float]:
        """计算北向/南向资金的累计流入（7日和30日）

        Args:
            direction: 资金方向，"north" 或 "south"

        Returns:
            包含 7日累计和30日累计的字典
        """
        # 获取最近30天的数据
        end = pd.Timestamp.now().normalize()
        start = (end - pd.Timedelta(days=40)).normalize()

        data = self.fetch_all_fund_flow(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

        if direction not in data or data[direction].empty:
            return {"cum_7d": None, "cum_30d": None}

        df = data[direction]

        # 过滤出最近的30个交易日
        df = df.sort_index(ascending=True).tail(30)

        # 计算7日累计和30日累计
        cum_7d = df.tail(7)["net_flow"].sum()
        cum_30d = df.tail(30)["net_flow"].sum()

        # 处理 NaN 值
        cum_7d = float(cum_7d) if pd.notna(cum_7d) else None
        cum_30d = float(cum_30d) if pd.notna(cum_30d) else None

        return {
            "cum_7d": cum_7d,
            "cum_30d": cum_30d
        }

    def get_cumulative_flow_data(self) -> Dict:
        """获取北向和南向资金的累计流入数据

        Returns:
            包含北向和南向累计流入数据的字典
        """
        north_cum = self.calculate_cumulative_flow("north")
        south_cum = self.calculate_cumulative_flow("south")

        end = pd.Timestamp.now().normalize()

        return {
            "north_cumulative": {
                "date": end.date(),
                "cum_7d": north_cum["cum_7d"],
                "cum_30d": north_cum["cum_30d"]
            },
            "south_cumulative": {
                "date": end.date(),
                "cum_7d": south_cum["cum_7d"],
                "cum_30d": south_cum["cum_30d"]
            }
        }


# 创建全局资金流向服务实例
_fund_flow_service: Optional[FundFlowService] = None


def get_fund_flow_service() -> FundFlowService:
    """获取资金流向服务单例

    Returns:
        资金流向服务实例
    """
    global _fund_flow_service
    if _fund_flow_service is None:
        _fund_flow_service = FundFlowService()
    return _fund_flow_service