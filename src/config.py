"""配置管理模块"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    # FRED API 配置
    fred_api_key: str

    # 服务配置
    service_port: int = 8094
    service_host: str = "0.0.0.0"

    # 数据配置
    data_dir: str = "./data"
    historical_start_date: str = "2000-01-01"

    # 重试配置
    max_retries: int = 3
    retry_delay: float = 1.0

    # FRED 数据代码
    fred_codes: dict = {
        "us_3m": "DGS3MO",
        "us_2y": "DGS2",
        "us_10y": "DGS10",
        # 德国国债收益率（OECD数据）
        "eu_3m": "IR3TIB01DEM156N",    # 德国3个月银行间利率
        "eu_10y": "IRLTLT01DEM156N",   # 德国10年期国债收益率
        # 日本国债收益率（OECD数据）
        "jp_3m": "IR3TIB01JPM156N",    # 日本3个月银行间利率
        "jp_10y": "IRLTLT01JPM156N",   # 日本10年期国债收益率
        # 汇率数据
        "dollar_index": "DTWEXBGS",    # 美元指数
        "usd_cny": "DEXCHUS",          # 美元兑人民币
        "usd_jpy": "DEXJPUS",          # 美元兑日元
        "usd_eur": "DEXUSEU",          # 美元兑欧元
    }


    # ECB FM 数据代码（欧元区国债收益率）
    # 注意：ECB 不提供德国单独的国债收益率数据
    # 由于德国是欧元区最大经济体，欧元区国债收益率以德国国债为基准
    # 因此使用欧元区数据作为德国国债的近似替代
    ecb_codes: dict = {
        # 欧元区国债收益率 - 用作德国国债近似替代
        "eu_2y_ecb": "FM/M.U2.EUR.4F.BB.U2_2Y.YLD",  # 欧元区2年期 -> 德国Schatz近似
        "eu_5y_ecb": "FM/M.U2.EUR.4F.BB.U2_5Y.YLD",  # 欧元区5年期 -> 德国Bobl近似
        "eu_10y_ecb": "FM/M.U2.EUR.4F.BB.U2_10Y.YLD", # 欧元区10年期 -> 德国Bund近似
    }

    class Config:
        env_file = ".env"
        case_sensitive = False


# 配置单例
_settings: Settings = None


def get_settings() -> Settings:
    """获取配置单例"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
