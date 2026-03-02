"""配置管理模块"""
from pydantic_settings import BaseSettings
from functools import lru_cache


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
        "eu_10y": "DGS10EUR",
        "jp_10y": "DGS10JPY",
    }

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()
