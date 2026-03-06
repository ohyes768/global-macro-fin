"""数据存储服务模块"""
import pandas as pd
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Tuple
from src.config import get_settings
from src.utils.logger import setup_logger

logger = setup_logger("data_service")
settings = get_settings()


class DataService:
    """数据存储服务类"""

    def __init__(self):
        """初始化数据服务"""
        self.data_dir = Path(settings.data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # CSV 文件路径
        self.files = {
            "us_treasuries": self.data_dir / "us_treasuries.csv",
            "eu_bonds": self.data_dir / "eu_bonds.csv",
            "jp_bonds": self.data_dir / "jp_bonds.csv",
            "exchange_rates": self.data_dir / "exchange_rates.csv"
        }

    def _ensure_file_exists(self, file_path: Path, columns: list) -> None:
        """确保 CSV 文件存在

        Args:
            file_path: 文件路径
            columns: 列名
        """
        if not file_path.exists():
            # 创建包含列名的空文件
            df = pd.DataFrame(columns=columns)
            df.index.name = "date"
            df.to_csv(file_path)
            logger.info(f"创建新文件: {file_path}")

    def load_data(self, data_type: str) -> pd.DataFrame:
        """加载 CSV 数据

        Args:
            data_type: 数据类型 (us_treasuries, eu_bonds, jp_bonds, exchange_rates)

        Returns:
            数据 DataFrame
        """
        file_path = self.files.get(data_type)
        if file_path is None:
            raise ValueError(f"未知的数据类型: {data_type}")

        if not file_path.exists():
            logger.warning(f"文件不存在: {file_path}")
            return pd.DataFrame()

        try:
            data = pd.read_csv(file_path, index_col=0, parse_dates=True)
            logger.info(f"成功加载 {data_type} 数据，共 {len(data)} 条记录")
            return data
        except Exception as e:
            logger.error(f"加载 {data_type} 数据失败: {str(e)}")
            return pd.DataFrame()

    def save_data(self, data_type: str, data: pd.DataFrame) -> None:
        """保存 CSV 数据

        Args:
            data_type: 数据类型
            data: 数据 DataFrame
        """
        file_path = self.files.get(data_type)
        if file_path is None:
            raise ValueError(f"未知的数据类型: {data_type}")

        try:
            data.to_csv(file_path)
            logger.info(f"成功保存 {data_type} 数据到 {file_path}")
        except Exception as e:
            logger.error(f"保存 {data_type} 数据失败: {str(e)}")
            raise

    def append_data(self, data_type: str, new_data: pd.DataFrame) -> None:
        """追加数据到 CSV

        Args:
            data_type: 数据类型
            new_data: 新数据
        """
        # 加载现有数据
        existing_data = self.load_data(data_type)

        if existing_data.empty:
            # 如果没有现有数据，直接保存新数据
            self.save_data(data_type, new_data)
        else:
            # 合并新旧数据
            combined = pd.concat([existing_data, new_data])
            # 删除重复的日期，保留最新的数据
            combined = combined[~combined.index.duplicated(keep="last")]
            # 排序
            combined = combined.sort_index()
            # 保存
            self.save_data(data_type, combined)
            logger.info(
                f"追加 {data_type} 数据: 新增 {len(new_data)} 条，"
                f"总计 {len(combined)} 条"
            )

    def get_last_date(self, data_type: str) -> Optional[pd.Timestamp]:
        """获取最后一条数据的日期

        Args:
            data_type: 数据类型

        Returns:
            最后日期或 None
        """
        data = self.load_data(data_type)
        if data.empty:
            return None
        return pd.Timestamp(data.index[-1]).normalize()

    def save_fred_data(self, data: Dict[str, pd.Series], key: str = "auto") -> None:
        """保存 FRED 数据到对应的 CSV 文件

        Args:
            data: FRED 数据字典
            key: 数据类型标识，"auto" 表示自动识别（默认），或指定具体类型
        """
        if key == "auto":
            self._save_by_auto_detection(data)
        elif key == "us_treasuries":
            self._save_us_treasuries(data)
        elif key == "eu_bonds":
            self._save_eu_bonds(data)
        elif key == "jp_bonds":
            self._save_jp_bonds(data)
        elif key == "exchange_rates":
            self._save_exchange_rates(data)

    def _save_by_auto_detection(self, data: Dict[str, pd.Series]) -> None:
        """根据数据键名自动识别并保存到对应的 CSV 文件

        Args:
            data: FRED 数据字典
        """
        us_keys = ["us_3m", "us_2y", "us_10y"]
        eu_keys = ["eu_10y", "eu_3m", "eu_2y", "eu_2y_ecb", "eu_5y"]
        jp_keys = ["jp_10y", "jp_3m"]
        exchange_keys = ["dollar_index", "usd_cny", "usd_jpy", "usd_eur"]

        us_data = {k: v for k, v in data.items() if k in us_keys and not v.empty}
        eu_data = {k: v for k, v in data.items() if k in eu_keys and not v.empty}
        jp_data = {k: v for k, v in data.items() if k in jp_keys and not v.empty}
        exchange_data = {k: v for k, v in data.items() if k in exchange_keys and not v.empty}

        if us_data:
            self._save_us_treasuries(us_data)
        if eu_data:
            self._save_eu_bonds(eu_data)
        if jp_data:
            self._save_jp_bonds(jp_data)
        if exchange_data:
            self._save_exchange_rates(exchange_data)

    def _save_us_treasuries(self, data: Dict[str, pd.Series]) -> None:
        """保存美国国债数据

        Args:
            data: 美债数据字典
        """
        us_data = {}
        for fred_key in ["us_3m", "us_2y", "us_10y"]:
            if fred_key in data and not data[fred_key].empty:
                col_name = fred_key.split("_")[1]
                us_data[col_name] = data[fred_key]

        if us_data:
            us_df = pd.DataFrame(us_data)
            us_df.columns = ["美债3m", "美债2y", "美债10y"]
            self._ensure_file_exists(self.files["us_treasuries"], ["美债3m", "美债2y", "美债10y"])
            self.append_data("us_treasuries", us_df)
            logger.info(f"已保存美债数据: {list(us_data.keys())}")

    def _save_eu_bonds(self, data: Dict[str, pd.Series]) -> None:
        """保存欧洲（德国）国债数据

        Args:
            data: 欧债数据字典
        """
        eu_data = {}
        col_mapping = {
            "eu_10y": "德债10y",
            "eu_3m": "德债3m",
            "eu_2y": "德债2y",
            "eu_2y_ecb": "德债2y",
            "eu_5y": "德债5y",
        }
        for fred_key in col_mapping:
            if fred_key in data and not data[fred_key].empty:
                eu_data[col_mapping[fred_key]] = data[fred_key]

        if eu_data:
            eu_df = pd.DataFrame(eu_data)
            self._ensure_file_exists(self.files["eu_bonds"], list(eu_data.keys()))
            self.append_data("eu_bonds", eu_df)
            logger.info(f"已保存欧债数据: {list(eu_data.keys())}")

    def _save_jp_bonds(self, data: Dict[str, pd.Series]) -> None:
        """保存日本国债数据

        Args:
            data: 日债数据字典
        """
        jp_data = {}
        col_mapping = {
            "jp_10y": "日债10y",
            "jp_3m": "日债3m",
        }
        for fred_key in col_mapping:
            if fred_key in data and not data[fred_key].empty:
                jp_data[col_mapping[fred_key]] = data[fred_key]

        if jp_data:
            jp_df = pd.DataFrame(jp_data)
            self._ensure_file_exists(self.files["jp_bonds"], list(jp_data.keys()))
            self.append_data("jp_bonds", jp_df)
            logger.info(f"已保存日债数据: {list(jp_data.keys())}")

    def _save_exchange_rates(self, data: Dict[str, pd.Series]) -> None:
        """保存汇率数据

        Args:
            data: 汇率数据字典
        """
        exchange_data = {}
        exchange_mapping = {
            "dollar_index": "美元指数",
            "usd_cny": "美元人民币",
            "usd_jpy": "美元日元",
            "usd_eur": "美元欧元"
        }

        for fred_key, col_name in exchange_mapping.items():
            if fred_key in data and not data[fred_key].empty:
                exchange_data[col_name] = data[fred_key]

        if exchange_data:
            exchange_df = pd.DataFrame(exchange_data)
            self._ensure_file_exists(self.files["exchange_rates"], ["美元指数", "美元人民币", "美元日元", "美元欧元"])
            self.append_data("exchange_rates", exchange_df)
            logger.info(f"已保存汇率数据: {list(exchange_data.keys())}")

    def query_data(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> Dict:
        """查询指定时间范围的数据

        Args:
            start_date: 起始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            查询结果字典
        """
        # 默认时间范围：最近90天
        if end_date is None:
            end_date = pd.Timestamp.now().normalize()
        else:
            end_date = pd.Timestamp(end_date)

        if start_date is None:
            start_date = end_date - pd.Timedelta(days=90)
        else:
            start_date = pd.Timestamp(start_date)

        result = {
            "dates": [],
            "us_treasuries": {"3m": [], "2y": [], "10y": []},
            "eu_treasuries": {"3m": [], "2y": [], "10y": []},
            "jp_treasuries": {"3m": [], "2y": [], "10y": []},
            "exchange_rates": {
                "dollar_index": [],
                "usd_cny": [],
                "usd_jpy": [],
                "usd_eur": []
            }
        }

        # 加载美国国债数据
        us_data = self.load_data("us_treasuries")
        if not us_data.empty:
            # 填充缺失值
            us_data = us_data.ffill()
            # 筛选时间范围
            us_filtered = us_data[(us_data.index >= start_date) & (us_data.index <= end_date)]
            result["dates"] = us_filtered.index.strftime("%Y-%m-%d").tolist()
            # 新列名映射到 API 格式
            col_mapping = {"美债3m": "3m", "美债2y": "2y", "美债10y": "10y"}
            for new_col, old_col in col_mapping.items():
                if new_col in us_filtered.columns:
                    result["us_treasuries"][old_col] = us_filtered[new_col].tolist()

        # 加载德债数据（月度数据，需要独立处理日期对齐）
        eu_data = self.load_data("eu_bonds")
        if not eu_data.empty:
            eu_data = eu_data.ffill()
            eu_filtered = eu_data[(eu_data.index >= start_date) & (eu_data.index <= end_date)]

            # 德债列名映射到API格式
            eu_col_mapping = {"德债3m": "3m", "德债2y": "2y", "德债10y": "10y"}

            # 创建一个包含所有日期的完整日期范围用于对齐
            target_index = us_data.index if not us_data.empty else pd.date_range(start_date, end_date)

            # 处理每个期限的数据
            for chinese_col, api_col in eu_col_mapping.items():
                if chinese_col in eu_filtered.columns and not eu_filtered.empty:
                    # 将月度数据对齐到美债的日期数组（前向填充）
                    eu_full = eu_data.reindex(target_index, method="ffill")
                    # 筛选时间范围
                    eu_aligned = eu_full[(eu_full.index >= start_date) & (eu_full.index <= end_date)]
                    result["eu_treasuries"][api_col] = eu_aligned[chinese_col].tolist()

        # 加载日债数据（月度数据，需要独立处理日期对齐）
        jp_data = self.load_data("jp_bonds")
        if not jp_data.empty:
            jp_data = jp_data.ffill()
            jp_filtered = jp_data[(jp_data.index >= start_date) & (jp_data.index <= end_date)]

            # 日债列名映射（优先使用"日债10y"，如果没有再使用"日债 10y"）
            jp_col = "日债10y" if "日债10y" in jp_filtered.columns else "日债 10y"

            if jp_col in jp_filtered.columns and not jp_filtered.empty:
                # 将月度数据对齐到美债的日期数组（前向填充）
                # 先创建一个包含所有日期的完整日期范围
                target_index = us_data.index if not us_data.empty else pd.date_range(start_date, end_date)
                # 先将日债数据重新索引到完整日期范围，然后前向填充
                jp_full = jp_data.reindex(target_index, method="ffill")
                # 再筛选时间范围
                jp_aligned = jp_full[(jp_full.index >= start_date) & (jp_full.index <= end_date)]
                result["jp_treasuries"]["10y"] = jp_aligned[jp_col].tolist()

        # 加载汇率数据
        exchange_data = self.load_data("exchange_rates")
        if not exchange_data.empty:
            exchange_data = exchange_data.ffill()
            exchange_filtered = exchange_data[(exchange_data.index >= start_date) & (exchange_data.index <= end_date)]

            # 汇率数据列名映射
            col_mapping = {
                "美元指数": "dollar_index",
                "美元人民币": "usd_cny",
                "美元日元": "usd_jpy",
                "美元欧元": "usd_eur"
            }

            for chinese_col, api_col in col_mapping.items():
                if chinese_col in exchange_filtered.columns:
                    result["exchange_rates"][api_col] = exchange_filtered[chinese_col].tolist()

        return result


# 创建全局数据服务实例
_data_service: Optional[DataService] = None


def get_data_service() -> DataService:
    """获取数据服务单例

    Returns:
        数据服务实例
    """
    global _data_service
    if _data_service is None:
        _data_service = DataService()
    return _data_service
