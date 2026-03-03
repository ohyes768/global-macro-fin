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


class USTreasuriesUpdateData(BaseModel):
    """美债更新响应数据"""

    us_treasuries: USTreasuries


class MacroData(BaseModel):
    """宏观经济数据"""

    us_treasuries: USTreasuries
    eu_10y: TreasuryData
    jp_10y: TreasuryData


class UpdateResponse(BaseModel):
    """更新响应"""

    success: bool
    message: str
    data: Optional[USTreasuriesUpdateData | MacroData] = None
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
