"""数据模型定义"""
from pydantic import BaseModel
from datetime import date
from typing import Optional, Dict, List


class TreasuryData(BaseModel):
    """国债数据"""

    date: date
    value: Optional[float] = None


class USTreasuries(BaseModel):
    """美国国债数据"""

    m3: TreasuryData
    y2: TreasuryData
    y10: TreasuryData


class EUTreasuries(BaseModel):
    """欧洲国债数据（德国）"""

    m3: TreasuryData
    y2: TreasuryData
    y10: TreasuryData


class JPTreasuries(BaseModel):
    """日本国债数据"""

    m3: TreasuryData
    y2: TreasuryData
    y10: TreasuryData


class USTreasuriesUpdateData(BaseModel):
    """美债更新响应数据"""

    us_treasuries: USTreasuries


class EUTreasuriesUpdateData(BaseModel):
    """欧债更新响应数据"""

    eu_treasuries: EUTreasuries


class JPTreasuriesUpdateData(BaseModel):
    """日债更新响应数据"""

    jp_treasuries: JPTreasuries


class MacroData(BaseModel):
    """宏观经济数据"""

    us_treasuries: USTreasuries
    eu_treasuries: EUTreasuries
    jp_treasuries: JPTreasuries


class ExchangeRateData(BaseModel):
    """汇率数据"""

    date: date
    value: Optional[float] = None


class ExchangeRates(BaseModel):
    """汇率数据"""

    dollar_index: ExchangeRateData
    usd_cny: ExchangeRateData
    usd_jpy: ExchangeRateData
    usd_eur: ExchangeRateData


class ExchangeRatesUpdateData(BaseModel):
    """汇率更新响应数据"""

    exchange_rates: ExchangeRates


class MacroDataWithRates(BaseModel):
    """宏观经济数据（包含汇率）"""

    us_treasuries: USTreasuries
    eu_treasuries: EUTreasuries
    jp_treasuries: JPTreasuries
    exchange_rates: ExchangeRates


class UpdateResponse(BaseModel):
    """更新响应"""

    success: bool
    message: str
    data: Optional[
        USTreasuriesUpdateData
        | EUTreasuriesUpdateData
        | JPTreasuriesUpdateData
        | MacroData
        | ExchangeRatesUpdateData
        | MacroDataWithRates
    ] = None
    updated_at: Optional[str] = None
    error_code: Optional[str] = None


class DataResponse(BaseModel):
    """数据查询响应"""

    success: bool
    message: str
    data: Optional[Dict] = None
    error_code: Optional[str] = None


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str
    service: str
    version: str
    last_update: Optional[str] = None
