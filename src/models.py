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
        | ChinaBondUpdateData
        | TedSpreadUpdateData
        | CommoditiesUpdateData
        | IndicesUpdateData
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


class ChinaBondData(BaseModel):
    """中国国债数据"""

    date: date
    value: Optional[float] = None  # 10年期国债收益率（%）


class ChinaBondUpdateData(BaseModel):
    """中国国债更新响应数据"""

    china_bond_10y: ChinaBondData


class TedSpreadData(BaseModel):
    """TED利差数据"""

    date: date
    sofr: Optional[float] = None    # SOFR 利率（%）
    us_3m: Optional[float] = None   # 美国3个月国债收益率（%）
    ted_spread: Optional[float] = None  # TED利差 = SOFR - DGS3MO（%）


class TedSpreadUpdateData(BaseModel):
    """TED利差更新响应数据"""

    ted_spread: TedSpreadData


class CommoditiesData(BaseModel):
    """商品数据（黄金/白银/原油/铜，统一走阿里云 alirmcom2）"""

    date: date
    gold: Optional[float] = None     # 黄金（元/克，SGEAU9999）
    silver: Optional[float] = None   # 白银（元/克，SGEAG9999）
    oil: Optional[float] = None      # 原油（美元/桶，UKOIL）
    copper: Optional[float] = None   # 铜（美元/吨，USHG）


class CommoditiesUpdateData(BaseModel):
    """商品更新响应数据"""

    commodities: CommoditiesData


class IndicesData(BaseModel):
    """5 个全球股指 K 线数据（恒生/上证/标普500/纳指/道指，统一走阿里云 alirmcom2 comkm）"""

    date: date
    HKHSI: Optional[float] = None       # 恒生指数
    SH000001: Optional[float] = None    # 上证指数
    SPX: Optional[float] = None         # 标普500
    IXIC: Optional[float] = None        # 纳斯达克综合
    DJI: Optional[float] = None         # 道琼斯


class IndicesUpdateData(BaseModel):
    """股指更新响应数据"""

    indices: IndicesData
