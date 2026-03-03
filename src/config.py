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
        # 德国10年期国债收益率（OECD数据）
        "eu_10y": "IRLTLT01DEM156N",
        # 日本10年期国债收益率（OECD数据）
        "jp_10y": "IRLTLT01JPM156N",
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
