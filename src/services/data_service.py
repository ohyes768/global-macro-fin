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
            data_type: 数据类型 (us_treasuries, eu_bonds, jp_bonds)

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

    def save_fred_data(self, data: Dict[str, pd.Series]) -> None:
        """保存 FRED 数据到对应的 CSV 文件

        Args:
            data: FRED 数据字典
        """
        # 保存美国国债数据
        us_data = {}
        for key in ["us_3m", "us_2y", "us_10y"]:
            if key in data and not data[key].empty:
                col_name = key.split("_")[1]  # 3m, 2y, 10y
                us_data[col_name] = data[key]

        if us_data:
            us_df = pd.DataFrame(us_data)
            us_df.columns = ["3m", "2y", "10y"]
            self._ensure_file_exists(self.files["us_treasuries"], ["3m", "2y", "10y"])
            self.append_data("us_treasuries", us_df)

        # 保存欧债数据
        if "eu_10y" in data and not data["eu_10y"].empty:
            eu_df = pd.DataFrame({"10y": data["eu_10y"]})
            self._ensure_file_exists(self.files["eu_bonds"], ["10y"])
            self.append_data("eu_bonds", eu_df)

        # 保存日债数据
        if "jp_10y" in data and not data["jp_10y"].empty:
            jp_df = pd.DataFrame({"10y": data["jp_10y"]})
            self._ensure_file_exists(self.files["jp_bonds"], ["10y"])
            self.append_data("jp_bonds", jp_df)

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

        result = {"dates": [], "us_treasuries": {"3m": [], "2y": [], "10y": []}, "eu_10y": [], "jp_10y": []}

        # 加载美国国债数据
        us_data = self.load_data("us_treasuries")
        if not us_data.empty:
            # 填充缺失值
            us_data = us_data.ffill()
            # 筛选时间范围
            us_filtered = us_data[(us_data.index >= start_date) & (us_data.index <= end_date)]
            result["dates"] = us_filtered.index.strftime("%Y-%m-%d").tolist()
            for col in ["3m", "2y", "10y"]:
                if col in us_filtered.columns:
                    result["us_treasuries"][col] = us_filtered[col].tolist()

        # 加载欧债数据
        eu_data = self.load_data("eu_bonds")
        if not eu_data.empty:
            eu_data = eu_data.ffill()
            eu_filtered = eu_data[(eu_data.index >= start_date) & (eu_data.index <= end_date)]
            if "10y" in eu_filtered.columns:
                result["eu_10y"] = eu_filtered["10y"].tolist()

        # 加载日债数据
        jp_data = self.load_data("jp_bonds")
        if not jp_data.empty:
            jp_data = jp_data.ffill()
            jp_filtered = jp_data[(jp_data.index >= start_date) & (jp_data.index <= end_date)]
            if "10y" in jp_filtered.columns:
                result["jp_10y"] = jp_filtered["10y"].tolist()

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
