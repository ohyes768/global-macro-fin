"""数据存储服务模块"""
import pandas as pd
import os
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Tuple
from src.config import get_settings
from src.utils.logger import setup_logger

logger = setup_logger("data_service")
settings = get_settings()


# ==================== query_data 缓存 ====================
# 缓存策略：全局版本号 + 5min TTL
# - 用版本号简化失效：所有 save_data() 末尾 _bump_cache_version()，
#   任何 CSV 写入都让所有缓存 key 失效（不需要精确找 to_csv 点）
# - 5min TTL 兜底：极端情况下（如忘记调 save_data），5min 后自然失效
_QUERY_CACHE_TTL_S = 300
_QUERY_CACHE_MAX_ENTRIES = 16
_QUERY_CACHE: Dict[Tuple, Tuple[float, Dict]] = {}
_QUERY_CACHE_LOCK = threading.Lock()
_CACHE_VERSION = 0  # 全局版本号：每次 CSV 写入 +1，所有缓存 key 失效


def _bump_cache_version() -> None:
    """CSV 写入后调用，让所有 query_data 缓存失效"""
    global _CACHE_VERSION
    _CACHE_VERSION += 1
    logger.debug(f"query_data 缓存版本号 bump 到 {_CACHE_VERSION}")


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
            "exchange_rates": self.data_dir / "exchange_rates.csv",
            "vix": self.data_dir / "vix.csv",
            "fund_flow": self.data_dir / "fund_flow.csv",
            "china_bond": self.data_dir / "china_bond.csv",
            "ted_spread": self.data_dir / "ted_spread.csv",
            "commodities": self.data_dir / "commodities.csv",
            "indices": self.data_dir / "indices.csv",
            "tga": self.data_dir / "tga.csv",
            "hibor": self.data_dir / "hibor.csv"
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
            data_type: 数据类型 (us_treasuries, eu_bonds, jp_bonds, exchange_rates, vix)

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
            # CSV 写入后让 query_data 缓存失效（任何保存路径都走这里）
            _bump_cache_version()
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
        elif key == "vix":
            self._save_vix(data)
        elif key == "tga":
            self._save_tga(data)
        elif key == "hibor":
            self._save_hibor(data)

    def _save_by_auto_detection(self, data: Dict[str, pd.Series]) -> None:
        """根据数据键名自动识别并保存到对应的 CSV 文件

        Args:
            data: FRED 数据字典
        """
        us_keys = ["us_3m", "us_2y", "us_10y"]
        eu_keys = ["eu_10y", "eu_3m", "eu_2y", "eu_2y_ecb", "eu_5y"]
        jp_keys = ["jp_10y", "jp_3m"]
        exchange_keys = ["dollar_index", "usd_cny", "usd_jpy", "usd_eur"]
        vix_keys = ["vix"]

        us_data = {k: v for k, v in data.items() if k in us_keys and not v.empty}
        eu_data = {k: v for k, v in data.items() if k in eu_keys and not v.empty}
        jp_data = {k: v for k, v in data.items() if k in jp_keys and not v.empty}
        exchange_data = {k: v for k, v in data.items() if k in exchange_keys and not v.empty}
        vix_data = {k: v for k, v in data.items() if k in vix_keys and not v.empty}

        if us_data:
            self._save_us_treasuries(us_data)
        if eu_data:
            self._save_eu_bonds(eu_data)
        if jp_data:
            self._save_jp_bonds(jp_data)
        if exchange_data:
            self._save_exchange_rates(exchange_data)
        if vix_data:
            self._save_vix(vix_data)

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

    def _save_vix(self, data: Dict[str, pd.Series]) -> None:
        """保存VIX数据

        Args:
            data: VIX数据字典
        """
        if "vix" not in data or data["vix"].empty:
            logger.warning("VIX数据为空，跳过保存")
            return

        vix_df = pd.DataFrame({"Close_VIX": data["vix"]})
        vix_df.index.name = "date"
        self._ensure_file_exists(self.files["vix"], ["Close_VIX"])
        self.append_data("vix", vix_df)
        logger.info(f"已保存VIX数据，共 {len(vix_df)} 条记录")

    def _save_tga(self, data: Dict[str, pd.Series]) -> None:
        """保存TGA账户余额数据（原始单位：百万美元，前端展示时 ÷1e5 转千亿美元）

        Args:
            data: TGA数据字典 {"tga": pd.Series}
        """
        if "tga" not in data or data["tga"].empty:
            logger.warning("TGA数据为空，跳过保存")
            return

        tga_df = pd.DataFrame({"Close_TGA": data["tga"]})
        tga_df.index.name = "date"
        self._ensure_file_exists(self.files["tga"], ["Close_TGA"])
        self.append_data("tga", tga_df)
        logger.info(f"已保存TGA数据，共 {len(tga_df)} 条记录")

    def _save_hibor(self, data: Dict[str, pd.Series]) -> None:
        """保存HIBOR隔夜拆息数据（单位：%）

        Args:
            data: HIBOR数据字典 {"hibor": pd.Series}
        """
        if "hibor" not in data or data["hibor"].empty:
            logger.warning("HIBOR数据为空，跳过保存")
            return

        hibor_df = pd.DataFrame({"HIBOR_Overnight": data["hibor"]})
        hibor_df.index.name = "date"
        self._ensure_file_exists(self.files["hibor"], ["HIBOR_Overnight"])
        self.append_data("hibor", hibor_df)
        logger.info(f"已保存HIBOR数据，共 {len(hibor_df)} 条记录")

    def _save_china_bond(self, data: Dict[str, pd.Series]) -> None:
        """保存中国国债数据

        Args:
            data: 中国国债数据字典
        """
        if not data or all(v.empty for v in data.values()):
            logger.warning("中国国债数据为空，跳过保存")
            return

        # 合并所有中国国债数据
        china_df = pd.DataFrame(data)
        china_df.columns = [f"中国{c}" for c in china_df.columns]
        china_df.index.name = "date"

        self._ensure_file_exists(self.files["china_bond"], list(china_df.columns))
        self.append_data("china_bond", china_df)
        logger.info(f"已保存中国国债数据，共 {len(china_df)} 条记录")

    def save_china_bond_data(self, data: Dict[str, pd.Series]) -> None:
        """保存中国国债数据

        Args:
            data: 中国国债数据字典
        """
        self._save_china_bond(data)

    def _save_ted_spread(self, data: Dict[str, pd.Series]) -> None:
        """保存TED利差数据

        Args:
            data: TED利差数据字典（包含 sofr, us_3m, ted_spread）
        """
        if not data or all(v.empty for v in data.values()):
            logger.warning("TED利差数据为空，跳过保存")
            return

        ted_df = pd.DataFrame(data)
        ted_df.columns = ["SOFR", "美债3m", "TED利差"]
        ted_df.index.name = "date"

        self._ensure_file_exists(self.files["ted_spread"], list(ted_df.columns))
        self.append_data("ted_spread", ted_df)
        logger.info(f"已保存TED利差数据，共 {len(ted_df)} 条记录")

    def save_commodities(self, new_data: Dict[str, pd.Series]) -> None:
        """保存 4 个商品日 K 线到 commodities.csv（按 date 对齐，缺失填 NaN）

        commodity_service.fetch_all() 返回 4 个 Series（已应用单位换算到展示单位），
        合并成 DataFrame 后走 append_data（合并 + 去重 + 排序），保证：
        - fetch/commodities/history 全量拉取 → 覆盖式写入
        - update/commodities 增量拉取 → 追加合并

        Args:
            new_data: {gold: Series, silver: Series, oil: Series, copper: Series}
                     失败的 symbol 对应空 Series（pd.DataFrame 会填 NaN 列）
                     Series.values 已换算到展示单位（元/克、$/桶、$/吨 等）
        """
        expected_cols = ["黄金", "白银", "原油", "铜"]

        if not new_data:
            logger.warning("商品数据为空，跳过保存")
            return

        # 合并 4 个 Series 成 DataFrame（按 date 对齐，缺失填 NaN）
        df = pd.DataFrame(new_data)
        # commodities.csv 用中文列名（query_data 期望），英文 key 翻译 → 再 reindex 稳列序
        df = df.rename(columns={
            "gold": "黄金", "silver": "白银", "oil": "原油", "copper": "铜",
        })
        # 稳定列顺序 + 缺失 symbol 补 NaN 列
        df = df.reindex(columns=expected_cols)
        df.index.name = "date"

        # 确保 CSV 文件存在（含 4 列 header）
        self._ensure_file_exists(self.files["commodities"], expected_cols)
        # append_data 处理合并+去重+排序（last 保留），保证增量更新不重复
        self.append_data("commodities", df)
        logger.info(f"已保存商品数据 {len(df)} 条，列: {list(df.columns)}")

    def save_ted_spread_data(self, sofr: pd.Series, us_3m: pd.Series) -> None:
        """保存TED利差数据

        Args:
            sofr: SOFR 数据
            us_3m: 美国3个月国债收益率数据
        """
        # 计算 TED 利差
        # 确保索引对齐
        sofr_aligned = sofr.reindex(us_3m.index, method="ffill")
        ted_spread = sofr_aligned - us_3m

        data = {
            "sofr": sofr_aligned,
            "us_3m": us_3m,
            "ted_spread": ted_spread
        }
        self._save_ted_spread(data)

    def save_fund_flow(self, data: Dict[str, pd.DataFrame]) -> None:
        """保存资金流向数据

        Args:
            data: 资金流向数据字典，包含 'north' 和 'south' 两个 DataFrame
        """
        if not data:
            logger.warning("资金流向数据为空，跳过保存")
            return

        # 合并北向和南向资金流向数据
        fund_flow_list = []
        columns = []

        if "north" in data and not data["north"].empty:
            north_df = data["north"].copy()
            north_df.columns = ["北向净流入", "北向买入", "北向卖出"]
            fund_flow_list.append(north_df)
            if not columns:
                columns = north_df.columns.tolist()

        if "south" in data and not data["south"].empty:
            south_df = data["south"].copy()
            south_df.columns = ["南向净流入", "南向买入", "南向卖出"]
            fund_flow_list.append(south_df)
            if not columns:
                columns = south_df.columns.tolist()
            else:
                columns.extend(south_df.columns.tolist())

        if not fund_flow_list:
            logger.warning("资金流向数据为空，跳过保存")
            return

        # 按日期合并北向和南向数据
        fund_flow_df = pd.concat(fund_flow_list, axis=1)

        # 设置索引名称
        fund_flow_df.index.name = "date"

        # 确保所有必要的列都存在
        all_columns = ["北向净流入", "北向买入", "北向卖出", "南向净流入", "南向买入", "南向卖出"]
        for col in all_columns:
            if col not in fund_flow_df.columns:
                fund_flow_df[col] = None

        # 只保留需要的列
        fund_flow_df = fund_flow_df[all_columns]

        # 确保文件存在
        self._ensure_file_exists(self.files["fund_flow"], all_columns)

        # 保存数据
        self.append_data("fund_flow", fund_flow_df)
        logger.info(f"已保存资金流向数据，共 {len(fund_flow_df)} 条记录")

    def save_indices(self, new_data: Dict[str, "pd.Series"]) -> None:
        """保存 5 个全球股指 K 线到 indices.csv（按 date 对齐，缺失填 NaN）

        index_service.fetch_all() 返回 5 个 Series，合并成 DataFrame 后走
        append_data（合并 + 去重 + 排序），保证：
        - fetch/indices/history 全量拉取 → 覆盖式写入
        - update/indices 增量拉取 → 追加合并

        Args:
            new_data: {HKHSI: Series(date->close), SH000001: Series, ...}
                     失败的 symbol 对应空 Series（pd.DataFrame 会填 NaN 列）
        """
        expected_cols = ["HKHSI", "SH000001", "SPX", "IXIC", "DJI"]

        if not new_data:
            logger.warning("股指数据为空，跳过保存")
            return

        # 合并 5 个 Series 成 DataFrame（按 date 对齐，缺失填 NaN）
        df = pd.DataFrame(new_data)
        # 稳定列顺序 + 缺失 symbol 补 NaN 列
        df = df.reindex(columns=expected_cols)
        df.index.name = "date"

        # 确保 CSV 文件存在（含 5 列 header）
        self._ensure_file_exists(self.files["indices"], expected_cols)
        # append_data 处理合并+去重+排序（last 保留），保证增量更新不重复
        self.append_data("indices", df)
        logger.info(f"已保存股指数据 {len(df)} 条，列: {list(df.columns)}")

    def query_data(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> Dict:
        """查询指定时间范围的数据（带 5min LRU 缓存）

        缓存策略：
        - key = (_CACHE_VERSION, start_date, end_date)
        - 命中条件：cache 存在 + now - ts < 5min
        - 失效：save_data() 末尾 _bump_cache_version()，所有 key 失效
        - 兜底：超过 _QUERY_CACHE_MAX_ENTRIES 清空，防内存爆

        Args:
            start_date: 起始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            查询结果字典
        """
        cache_key = (_CACHE_VERSION, start_date, end_date)
        now = time.time()

        with _QUERY_CACHE_LOCK:
            cached = _QUERY_CACHE.get(cache_key)
            if cached is not None:
                ts, data = cached
                if now - ts < _QUERY_CACHE_TTL_S:
                    logger.debug(f"query_data 缓存命中: key={cache_key}")
                    return data
                # 过期，删除
                del _QUERY_CACHE[cache_key]

        # 缓存未命中：执行实际查询
        data = self._query_data_impl(start_date, end_date)

        with _QUERY_CACHE_LOCK:
            _QUERY_CACHE[cache_key] = (now, data)
            # 超过 max entries 清空（防内存爆）
            if len(_QUERY_CACHE) > _QUERY_CACHE_MAX_ENTRIES:
                _QUERY_CACHE.clear()
                logger.debug("query_data 缓存超过上限已清空")

        return data

    def _query_data_impl(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> Dict:
        """查询指定时间范围的数据（实际实现，无缓存）

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
            },
            "vix": [],
            "fund_flow": {
                "north_net_flow": [],
                "north_buy": [],
                "north_sell": [],
                "south_net_flow": [],
                "south_buy": [],
                "south_sell": []
            },
            "china_bond": {
                "10y": [],
                "spread_10y_2y": []
            },
            "ted_spread": {
                "sofr": [],
                "us_3m": [],
                "ted_spread": []
            },
            "commodities": {
                "gold": [],
                "silver": [],
                "oil": [],
                "copper": []
            },
            "indices": {
                "HKHSI": [],
                "SH000001": [],
                "SPX": [],
                "IXIC": [],
                "DJI": []
            },
            "tga": [],
            "hibor": []
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

        # 加载VIX数据
        vix_data = self.load_data("vix")
        if not vix_data.empty:
            vix_data = vix_data.ffill()
            vix_filtered = vix_data[(vix_data.index >= start_date) & (vix_data.index <= end_date)]

            # 将VIX数据对齐到美债的日期数组（前向填充）
            if "Close_VIX" in vix_filtered.columns and not vix_filtered.empty:
                target_index = us_data.index if not us_data.empty else pd.date_range(start_date, end_date)
                vix_full = vix_data.reindex(target_index, method="ffill")
                vix_aligned = vix_full[(vix_full.index >= start_date) & (vix_full.index <= end_date)]
                result["vix"] = vix_aligned["Close_VIX"].tolist()

        # 加载资金流向数据
        fund_flow_data = self.load_data("fund_flow")
        if not fund_flow_data.empty:
            fund_flow_data = fund_flow_data.ffill()
            fund_flow_filtered = fund_flow_data[(fund_flow_data.index >= start_date) & (fund_flow_data.index <= end_date)]

            # 资金流向数据列名映射
            col_mapping = {
                "北向净流入": "north_net_flow",
                "北向买入": "north_buy",
                "北向卖出": "north_sell",
                "南向净流入": "south_net_flow",
                "南向买入": "south_buy",
                "南向卖出": "south_sell"
            }

            # 将资金流向数据对齐到美债的日期数组（前向填充）
            target_index = us_data.index if not us_data.empty else pd.date_range(start_date, end_date)
            fund_flow_full = fund_flow_data.reindex(target_index, method="ffill")
            fund_flow_aligned = fund_flow_full[(fund_flow_full.index >= start_date) & (fund_flow_full.index <= end_date)]

            for chinese_col, api_col in col_mapping.items():
                if chinese_col in fund_flow_aligned.columns:
                    result["fund_flow"][api_col] = fund_flow_aligned[chinese_col].tolist()

        # 加载中国国债数据
        china_bond_data = self.load_data("china_bond")
        if not china_bond_data.empty:
            china_bond_data = china_bond_data.ffill()
            china_bond_filtered = china_bond_data[(china_bond_data.index >= start_date) & (china_bond_data.index <= end_date)]

            # 查找10年期国债收益率列
            col_10y = None
            for col in china_bond_data.columns:
                col_str = str(col).lower()
                if "10y" in col_str or "10年" in col_str:
                    col_10y = col
                    break

            if col_10y is None and not china_bond_data.empty:
                # 默认使用第一列
                col_10y = china_bond_data.columns[0]

            if col_10y:
                # 将中国国债数据对齐到美债的日期数组（前向填充）
                target_index = us_data.index if not us_data.empty else pd.date_range(start_date, end_date)
                china_bond_full = china_bond_data.reindex(target_index, method="ffill")
                china_bond_aligned = china_bond_full[(china_bond_full.index >= start_date) & (china_bond_full.index <= end_date)]
                result["china_bond"]["10y"] = china_bond_aligned[col_10y].tolist()

                # 查找"中国10年-2年"期限利差列（与 10y 列独立查找，避免被含"10年"的匹配误命中）
                col_spread = next((c for c in china_bond_data.columns if "10年-2年" in str(c) or "spread" in str(c).lower()), None)
                if col_spread:
                    result["china_bond"]["spread_10y_2y"] = china_bond_aligned[col_spread].tolist()

        # 加载TED利差数据
        ted_data = self.load_data("ted_spread")
        if not ted_data.empty:
            ted_data = ted_data.ffill()
            ted_filtered = ted_data[(ted_data.index >= start_date) & (ted_data.index <= end_date)]

            # TED利差列名映射
            col_mapping = {
                "SOFR": "sofr",
                "美债3m": "us_3m",
                "TED利差": "ted_spread"
            }

            # 将TED利差数据对齐到美债的日期数组（前向填充）
            target_index = us_data.index if not us_data.empty else pd.date_range(start_date, end_date)
            ted_full = ted_data.reindex(target_index, method="ffill")
            ted_aligned = ted_full[(ted_full.index >= start_date) & (ted_full.index <= end_date)]

            for col, api_col in col_mapping.items():
                if col in ted_aligned.columns:
                    result["ted_spread"][api_col] = ted_aligned[col].tolist()

        # 加载商品数据
        commodity_data = self.load_data("commodities")
        if not commodity_data.empty:
            commodity_data = commodity_data.ffill()

            # 将商品数据对齐到美债的日期数组（前向填充）
            # 这保证 commodities 各字段长度与 dates 一致，前端 Plotly 才能正确配对 x/y
            target_index = us_data.index if not us_data.empty else pd.date_range(start_date, end_date)

            # 兼容老 CSV（无 silver 列）：reindex columns 自动补 NaN，前端 Plotly 会自动断开
            expected_cols = ["黄金", "白银", "原油", "铜"]
            commodity_aligned = commodity_data.reindex(columns=expected_cols)
            commodity_full = commodity_aligned.reindex(target_index, method="ffill")
            commodity_filtered = commodity_full[(commodity_full.index >= start_date) & (commodity_full.index <= end_date)]

            col_mapping = {
                "黄金": "gold",
                "白银": "silver",
                "原油": "oil",
                "铜": "copper",
            }

            for chinese_col, api_col in col_mapping.items():
                if chinese_col in commodity_filtered.columns:
                    result["commodities"][api_col] = commodity_filtered[chinese_col].tolist()

        # 加载全球股指数据（恒生/上证/标普500/纳指/道指）
        indices_data = self.load_data("indices")
        if not indices_data.empty:
            indices_data = indices_data.ffill()

            # 与 commodities 一致：reindex 到 target_index 保证长度对齐 dates
            target_index = us_data.index if not us_data.empty else pd.date_range(start_date, end_date)
            indices_aligned = indices_data.reindex(target_index, method="ffill")
            indices_filtered = indices_aligned[(indices_aligned.index >= start_date) & (indices_aligned.index <= end_date)]

            # 列名直接用 symbol（HKHSI/SH000001/SPX/IXIC/DJI），与前端 EconomicDataResponse.indices 对应
            for col in ["HKHSI", "SH000001", "SPX", "IXIC", "DJI"]:
                if col in indices_filtered.columns:
                    result["indices"][col] = indices_filtered[col].tolist()

        # 加载TGA账户余额数据（对齐到美债日期数组）
        tga_data = self.load_data("tga")
        if not tga_data.empty:
            tga_data = tga_data.ffill()
            tga_filtered = tga_data[(tga_data.index >= start_date) & (tga_data.index <= end_date)]
            if "Close_TGA" in tga_filtered.columns and not tga_filtered.empty:
                target_index = us_data.index if not us_data.empty else pd.date_range(start_date, end_date)
                tga_full = tga_data.reindex(target_index, method="ffill")
                tga_aligned = tga_full[(tga_full.index >= start_date) & (tga_full.index <= end_date)]
                result["tga"] = tga_aligned["Close_TGA"].tolist()

        # 加载HIBOR隔夜拆息数据（对齐到美债日期数组）
        hibor_data = self.load_data("hibor")
        if not hibor_data.empty:
            hibor_data = hibor_data.ffill()
            hibor_filtered = hibor_data[(hibor_data.index >= start_date) & (hibor_data.index <= end_date)]
            if "HIBOR_Overnight" in hibor_filtered.columns and not hibor_filtered.empty:
                target_index = us_data.index if not us_data.empty else pd.date_range(start_date, end_date)
                hibor_full = hibor_data.reindex(target_index, method="ffill")
                hibor_aligned = hibor_full[(hibor_full.index >= start_date) & (hibor_full.index <= end_date)]
                result["hibor"] = hibor_aligned["HIBOR_Overnight"].tolist()

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
