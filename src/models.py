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

    m3: Optional[TreasuryData] = None
    y2: Optional[TreasuryData] = None
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


class VIXData(BaseModel):
    """VIX恐慌指数数据"""

    date: date
    value: Optional[float] = None


class VIXUpdateData(BaseModel):
    """VIX更新响应数据"""

    vix: VIXData


class FundFlowData(BaseModel):
    """资金流向数据"""

    date: date
    net_flow: Optional[float] = None  # 净流入（亿元）
    buy: Optional[float] = None       # 买入额（亿元）
    sell: Optional[float] = None      # 卖出额（亿元）


class FundFlow(BaseModel):
    """资金流向"""

    north: FundFlowData  # 北向资金（港股通→A股）
    south: FundFlowData  # 南向资金（A股→港股通）


class FundFlowCumulativeData(BaseModel):
    """资金流向累计数据"""

    date: date
    cum_7d: Optional[float] = None  # 7日累计净流入（亿元）
    cum_30d: Optional[float] = None  # 30日累计净流入（亿元）


class FundFlowWithCumulative(BaseModel):
    """资金流向（包含累计数据）"""

    north: FundFlowData  # 北向资金（港股通→A股）
    south: FundFlowData  # 南向资金（A股→港股通）
    north_cumulative: FundFlowCumulativeData  # 北向资金累计数据
    south_cumulative: FundFlowCumulativeData  # 南向资金累计数据


class FundFlowUpdateData(BaseModel):
    """资金流向更新响应数据"""

    fund_flow: FundFlow


class FundFlowCumulativeResponse(BaseModel):
    """资金流向累计数据响应"""

    north_cumulative: FundFlowCumulativeData  # 北向资金累计数据
    south_cumulative: FundFlowCumulativeData  # 南向资金累计数据


class FundFlowHistoryItem(BaseModel):
    """资金流向历史数据项"""

    date: str
    north_net: Optional[float] = None    # 北向净流入
    north_buy: Optional[float] = None    # 北向买入
    north_sell: Optional[float] = None   # 北向卖出
    south_net: Optional[float] = None    # 南向净流入
    south_buy: Optional[float] = None    # 南向买入
    south_sell: Optional[float] = None   # 南向卖出


class FundFlowHistoryResponse(BaseModel):
    """资金流向历史数据响应"""

    data: List[FundFlowHistoryItem]


class MacroDataWithRates(BaseModel):
    """宏观经济数据（包含汇率）"""

    us_treasuries: USTreasuries
    eu_treasuries: EUTreasuries
    jp_treasuries: JPTreasuries
    exchange_rates: ExchangeRates


class MacroDataWithRatesAndVIX(BaseModel):
    """宏观经济数据（包含汇率和VIX）"""

    us_treasuries: USTreasuries
    eu_treasuries: EUTreasuries
    jp_treasuries: JPTreasuries
    exchange_rates: ExchangeRates
    vix: VIXData


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
        | VIXUpdateData
        | MacroDataWithRatesAndVIX
        | FundFlowUpdateData
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
