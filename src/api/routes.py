"""API 路由模块"""
print("[INIT-20260303-0942] routes.py 模块已加载")
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
import pandas as pd
from typing import Optional

from src.models import (
    UpdateResponse,
    DataResponse,
    HealthResponse,
    MacroData,
    MacroDataWithRates,
    MacroDataWithRatesAndVIX,
    TreasuryData,
    USTreasuries,
    EUTreasuries,
    JPTreasuries,
    USTreasuriesUpdateData,
    EUTreasuriesUpdateData,
    JPTreasuriesUpdateData,
    ExchangeRateData,
    ExchangeRates,
    ExchangeRatesUpdateData,
    VIXData,
    VIXUpdateData,
)
from src.services.fred_service import get_fred_service
from src.services.ecb_service import get_ecb_service
from src.services.data_service import get_data_service
from src.services.vix_service import get_vix_service
from src.utils.logger import setup_logger
from src.config import get_settings

logger = setup_logger("api_routes")
settings = get_settings()

router = APIRouter(prefix="/api/macro", tags=["macro"])

# 并发控制锁
_update_lock = None
_is_updating = False


async def acquire_update_lock():
    """获取更新锁"""
    global _is_updating
    _is_updating = True


def release_update_lock():
    """释放更新锁"""
    global _is_updating
    _is_updating = False


def is_updating() -> bool:
    """检查是否正在更新"""
    return _is_updating


async def _fetch_us_treasuries(
    fred_service, start_date: pd.Timestamp, end_date: pd.Timestamp
) -> dict:
    """获取美国国债数据的内部函数

    Args:
        fred_service: FRED 服务实例
        start_date: 起始日期
        end_date: 结束日期

    Returns:
        美债数据字典
    """
    logger.info(f"获取美国国债数据范围: {start_date} 到 {end_date}")

    us_data = {}
    us_codes = {"us_3m", "us_2y", "us_10y"}

    for name in us_codes:
        code = settings.fred_codes[name]
        try:
            series = await fred_service.fetch_series(code, start_date, end_date)
            us_data[name] = series
        except Exception as e:
            logger.error(f"获取 {name} ({code}) 数据时出错: {e}")
            us_data[name] = pd.Series(dtype="float64")

    return us_data


async def _fetch_oecd_bonds(
    fred_service, start_date: pd.Timestamp, end_date: pd.Timestamp
) -> dict:
    """获取 OECD 债券数据的内部函数

    Args:
        fred_service: FRED 服务实例
        start_date: 起始日期
        end_date: 结束日期

    Returns:
        OECD 债券数据字典
    """
    logger.info(f"获取 OECD 债券数据范围: {start_date} 到 {end_date}")

    oecd_data = {}
    ecb_service = get_ecb_service()

    # FRED 数据代码
    fred_bond_codes = {"eu_3m", "eu_10y", "jp_10y"}

    # ECB 数据代码（德债 2年期、5年期）
    ecb_bond_codes = {"eu_2y_ecb"}

    # 从 FRED 获取数据
    for name in fred_bond_codes:
        if name not in settings.fred_codes:
            continue
        code = settings.fred_codes[name]
        try:
            series = await fred_service.fetch_series(code, start_date, end_date)
            oecd_data[name] = series
        except Exception as e:
            logger.error(f"获取 {name} ({code}) 数据时出错: {e}")
            oecd_data[name] = pd.Series(dtype="float64")

    # 从 ECB 获取数据
    for name in ecb_bond_codes:
        try:
            series = await ecb_service.fetch_series(name, start_date, end_date)
            oecd_data[name] = series
        except Exception as e:
            logger.error(f"获取 {name} (ECB) 数据时出错: {e}")
            oecd_data[name] = pd.Series(dtype="float64")

    return oecd_data




async def _fetch_exchange_rates(
    fred_service, start_date: pd.Timestamp, end_date: pd.Timestamp
) -> dict:
    """获取汇率数据的内部函数

    Args:
        fred_service: FRED 服务实例
        start_date: 起始日期
        end_date: 结束日期

    Returns:
        汇率数据字典
    """
    logger.info(f"获取汇率数据范围: {start_date} 到 {end_date}")

    exchange_data = await fred_service.fetch_exchange_rates(start_date, end_date)
    return exchange_data

def _build_response_data(new_data: dict, end_date: pd.Timestamp) -> MacroData:
    """构建响应数据的内部函数（不包含汇率）

    Args:
        new_data: 新获取的数据字典
        end_date: 结束日期

    Returns:
        MacroData 响应对象
    """
    latest = {}
    for name, series in new_data.items():
        if not series.empty:
            last_idx = series.last_valid_index()
            if last_idx is not None:
                latest[name] = {"date": last_idx.strftime("%Y-%m-%d"), "value": float(series[last_idx])}

    us_m3 = latest.get("us_3m", TreasuryData(date=end_date.date(), value=None))
    us_y2 = latest.get("us_2y", TreasuryData(date=end_date.date(), value=None))
    us_y10 = latest.get("us_10y", TreasuryData(date=end_date.date(), value=None))
    eu_m3 = latest.get("eu_3m", TreasuryData(date=end_date.date(), value=None))
    eu_y2 = latest.get("eu_2y_ecb", TreasuryData(date=end_date.date(), value=None))
    eu_y10 = latest.get("eu_10y", TreasuryData(date=end_date.date(), value=None))
    jp_y10 = latest.get("jp_10y", TreasuryData(date=end_date.date(), value=None))

    return MacroData(
        us_treasuries=USTreasuries(m3=us_m3, y2=us_y2, y10=us_y10),
        eu_treasuries=EUTreasuries(m3=eu_m3, y2=eu_y2, y10=eu_y10),
        jp_treasuries=JPTreasuries(y10=jp_y10),
    )



def _build_response_data_with_rates(
    new_data: dict, exchange_data: dict, end_date: pd.Timestamp
) -> MacroDataWithRates:
    """构建包含汇率的响应数据的内部函数

    Args:
        new_data: 新获取的债券数据字典
        exchange_data: 新获取的汇率数据字典
        end_date: 结束日期

    Returns:
        MacroDataWithRates 响应对象
    """
    # 处理债券数据
    latest = {}
    for name, series in new_data.items():
        if not series.empty:
            last_idx = series.last_valid_index()
            if last_idx is not None:
                latest[name] = {"date": last_idx.strftime("%Y-%m-%d"), "value": float(series[last_idx])}

    # 处理汇率数据
    latest_rates = {}
    for name, series in exchange_data.items():
        if not series.empty:
            last_idx = series.last_valid_index()
            if last_idx is not None:
                latest_rates[name] = {"date": last_idx.strftime("%Y-%m-%d"), "value": float(series[last_idx])}

    us_m3 = latest.get("us_3m", TreasuryData(date=end_date.date(), value=None))
    us_y2 = latest.get("us_2y", TreasuryData(date=end_date.date(), value=None))
    us_y10 = latest.get("us_10y", TreasuryData(date=end_date.date(), value=None))
    eu_y10 = latest.get("eu_10y", TreasuryData(date=end_date.date(), value=None))
    jp_y10 = latest.get("jp_10y", TreasuryData(date=end_date.date(), value=None))

    dollar_index = latest_rates.get("dollar_index", ExchangeRateData(date=end_date.date(), value=None))
    usd_cny = latest_rates.get("usd_cny", ExchangeRateData(date=end_date.date(), value=None))
    usd_jpy = latest_rates.get("usd_jpy", ExchangeRateData(date=end_date.date(), value=None))
    usd_eur = latest_rates.get("usd_eur", ExchangeRateData(date=end_date.date(), value=None))

    return MacroDataWithRates(
        us_treasuries=USTreasuries(m3=us_m3, y2=us_y2, y10=us_y10),
        eu_treasuries=EUTreasuries(m3=eu_m3, y2=eu_y2, y10=eu_y10),
        jp_treasuries=JPTreasuries(y10=jp_y10),
        exchange_rates=ExchangeRates(
            dollar_index=dollar_index,
            usd_cny=usd_cny,
            usd_jpy=usd_jpy,
            usd_eur=usd_eur,
        ),
    )


@router.post("/fetch/us-treasuries/history", response_model=UpdateResponse)
async def fetch_us_treasuries_history():
    """获取美国国债历史数据接口 - 从 2000 年开始获取全部历史数据"""
    global _is_updating

    if _is_updating:
        return UpdateResponse(
            success=False,
            message="数据更新正在进行中，请稍后再试",
            error_code="UPDATE_IN_PROGRESS"
        )

    await acquire_update_lock()

    try:
        logger.info("开始获取美国国债历史数据...")
        fred_service = get_fred_service()
        data_service = get_data_service()

        latest_end = pd.Timestamp.now().normalize()
        us_start = pd.Timestamp(settings.historical_start_date)

        logger.info(f"获取美债历史数据，从 {us_start} 到 {latest_end}")

        new_data = await _fetch_us_treasuries(fred_service, us_start, latest_end)

        if not any(not series.empty for series in new_data.values()):
            raise Exception("未能获取到任何美债数据")

        data_service.save_fred_data(new_data)

        # 构建只包含美债的响应数据
        latest = {}
        for name, series in new_data.items():
            if not series.empty:
                last_idx = series.last_valid_index()
                if last_idx is not None:
                    latest[name] = {"date": last_idx.strftime("%Y-%m-%d"), "value": float(series[last_idx])}

        us_m3 = latest.get("us_3m", TreasuryData(date=latest_end.date(), value=None))
        us_y2 = latest.get("us_2y", TreasuryData(date=latest_end.date(), value=None))
        us_y10 = latest.get("us_10y", TreasuryData(date=latest_end.date(), value=None))

        response_data = USTreasuriesUpdateData(
            us_treasuries=USTreasuries(m3=us_m3, y2=us_y2, y10=us_y10)
        )

        logger.info("美国国债历史数据获取成功")
        return UpdateResponse(
            success=True,
            message="美国国债历史数据获取成功",
            data=response_data,
            updated_at=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"获取美国国债历史数据失败: {str(e)}")
        return UpdateResponse(
            success=False,
            message=f"获取美国国债历史数据失败: {str(e)}",
            error_code="UPDATE_FAILED"
        )
    finally:
        release_update_lock()


@router.post("/update/us-treasuries", response_model=UpdateResponse)
async def update_us_treasuries():
    """更新美国国债数据接口 - 增量更新最近 7 天的数据"""
    global _is_updating

    if _is_updating:
        return UpdateResponse(
            success=False,
            message="数据更新正在进行中，请稍后再试",
            error_code="UPDATE_IN_PROGRESS"
        )

    await acquire_update_lock()

    try:
        logger.info("开始增量更新美国国债数据...")
        fred_service = get_fred_service()
        data_service = get_data_service()

        latest_end = pd.Timestamp.now().normalize()
        us_start = (latest_end - pd.Timedelta(days=7)).normalize()

        logger.info(f"增量更新美债数据，从 {us_start} 到 {latest_end}")

        new_data = await _fetch_us_treasuries(fred_service, us_start, latest_end)

        if not any(not series.empty for series in new_data.values()):
            raise Exception("未能获取到任何美债新数据")

        data_service.save_fred_data(new_data)

        # 构建只包含美债的响应数据
        latest = {}
        for name, series in new_data.items():
            if not series.empty:
                last_idx = series.last_valid_index()
                if last_idx is not None:
                    latest[name] = {"date": last_idx.strftime("%Y-%m-%d"), "value": float(series[last_idx])}

        us_m3 = latest.get("us_3m", TreasuryData(date=latest_end.date(), value=None))
        us_y2 = latest.get("us_2y", TreasuryData(date=latest_end.date(), value=None))
        us_y10 = latest.get("us_10y", TreasuryData(date=latest_end.date(), value=None))

        response_data = USTreasuriesUpdateData(
            us_treasuries=USTreasuries(m3=us_m3, y2=us_y2, y10=us_y10)
        )

        logger.info("美国国债数据增量更新成功")
        return UpdateResponse(
            success=True,
            message="美国国债数据增量更新成功",
            data=response_data,
            updated_at=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"美国国债数据增量更新失败: {str(e)}")
        return UpdateResponse(
            success=False,
            message=f"美国国债数据增量更新失败: {str(e)}",
            error_code="UPDATE_FAILED"
        )
    finally:
        release_update_lock()


@router.post("/fetch/exchange-rates/history", response_model=UpdateResponse)
async def fetch_exchange_rates_history():
    """获取汇率历史数据接口 - 从 2000 年开始获取全部历史数据"""
    global _is_updating

    if _is_updating:
        return UpdateResponse(
            success=False,
            message="数据更新正在进行中，请稍后再试",
            error_code="UPDATE_IN_PROGRESS"
        )

    await acquire_update_lock()

    try:
        logger.info("开始获取汇率历史数据...")
        fred_service = get_fred_service()
        data_service = get_data_service()

        latest_end = pd.Timestamp.now().normalize()
        start_date = pd.Timestamp(settings.historical_start_date)

        logger.info(f"获取汇率历史数据，从 {start_date} 到 {latest_end}")

        exchange_data = await _fetch_exchange_rates(fred_service, start_date, latest_end)

        if not any(not series.empty for series in exchange_data.values()):
            raise Exception("未能获取到任何汇率数据")

        # 保存汇率数据
        data_service.save_fred_data(exchange_data, key="exchange_rates")

        # 构建只包含汇率的响应数据
        latest_rates = {}
        for name, series in exchange_data.items():
            if not series.empty:
                last_idx = series.last_valid_index()
                if last_idx is not None:
                    latest_rates[name] = {"date": last_idx.strftime("%Y-%m-%d"), "value": float(series[last_idx])}

        dollar_index = latest_rates.get("dollar_index", ExchangeRateData(date=latest_end.date(), value=None))
        usd_cny = latest_rates.get("usd_cny", ExchangeRateData(date=latest_end.date(), value=None))
        usd_jpy = latest_rates.get("usd_jpy", ExchangeRateData(date=latest_end.date(), value=None))
        usd_eur = latest_rates.get("usd_eur", ExchangeRateData(date=latest_end.date(), value=None))

        response_data = ExchangeRatesUpdateData(
            exchange_rates=ExchangeRates(
                dollar_index=dollar_index,
                usd_cny=usd_cny,
                usd_jpy=usd_jpy,
                usd_eur=usd_eur,
            )
        )

        logger.info("汇率历史数据获取成功")
        return UpdateResponse(
            success=True,
            message="汇率历史数据获取成功",
            data=response_data,
            updated_at=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"获取汇率历史数据失败: {str(e)}")
        return UpdateResponse(
            success=False,
            message=f"获取汇率历史数据失败: {str(e)}",
            error_code="UPDATE_FAILED"
        )
    finally:
        release_update_lock()


@router.post("/update/exchange-rates", response_model=UpdateResponse)
async def update_exchange_rates():
    """更新汇率数据接口 - 增量更新最近 7 天的数据"""
    global _is_updating

    if _is_updating:
        return UpdateResponse(
            success=False,
            message="数据更新正在进行中，请稍后再试",
            error_code="UPDATE_IN_PROGRESS"
        )

    await acquire_update_lock()

    try:
        logger.info("开始增量更新汇率数据...")
        fred_service = get_fred_service()
        data_service = get_data_service()

        latest_end = pd.Timestamp.now().normalize()
        start_date = (latest_end - pd.Timedelta(days=7)).normalize()

        logger.info(f"增量更新汇率数据，从 {start_date} 到 {latest_end}")

        exchange_data = await _fetch_exchange_rates(fred_service, start_date, latest_end)

        if not any(not series.empty for series in exchange_data.values()):
            raise Exception("未能获取到任何汇率新数据")

        # 保存汇率数据
        data_service.save_fred_data(exchange_data, key="exchange_rates")

        # 构建只包含汇率的响应数据
        latest_rates = {}
        for name, series in exchange_data.items():
            if not series.empty:
                last_idx = series.last_valid_index()
                if last_idx is not None:
                    latest_rates[name] = {"date": last_idx.strftime("%Y-%m-%d"), "value": float(series[last_idx])}

        dollar_index = latest_rates.get("dollar_index", ExchangeRateData(date=latest_end.date(), value=None))
        usd_cny = latest_rates.get("usd_cny", ExchangeRateData(date=latest_end.date(), value=None))
        usd_jpy = latest_rates.get("usd_jpy", ExchangeRateData(date=latest_end.date(), value=None))
        usd_eur = latest_rates.get("usd_eur", ExchangeRateData(date=latest_end.date(), value=None))

        response_data = ExchangeRatesUpdateData(
            exchange_rates=ExchangeRates(
                dollar_index=dollar_index,
                usd_cny=usd_cny,
                usd_jpy=usd_jpy,
                usd_eur=usd_eur,
            )
        )

        logger.info("汇率数据增量更新成功")
        return UpdateResponse(
            success=True,
            message="汇率数据增量更新成功",
            data=response_data,
            updated_at=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"汇率数据增量更新失败: {str(e)}")
        return UpdateResponse(
            success=False,
            message=f"汇率数据增量更新失败: {str(e)}",
            error_code="UPDATE_FAILED"
        )
    finally:
        release_update_lock()




@router.post("/fetch/eu-bonds/history", response_model=UpdateResponse)
async def fetch_eu_bonds_history():
    """获取欧洲（德国）国债历史数据接口 - 从 2000 年开始获取全部历史数据"""
    global _is_updating

    if _is_updating:
        return UpdateResponse(
            success=False,
            message="数据更新正在进行中，请稍后再试",
            error_code="UPDATE_IN_PROGRESS"
        )

    await acquire_update_lock()

    try:
        logger.info("开始获取欧洲国债历史数据...")
        fred_service = get_fred_service()
        data_service = get_data_service()

        latest_end = pd.Timestamp.now().normalize()
        start_date = pd.Timestamp(settings.historical_start_date)

        logger.info(f"获取欧债历史数据，从 {start_date} 到 {latest_end}")

        eu_data = await _fetch_oecd_bonds(fred_service, start_date, latest_end)
        eu_only = {k: v for k, v in eu_data.items() if k.startswith("eu_")}

        if not any(not series.empty for series in eu_only.values()):
            raise Exception("未能获取到任何欧债数据")

        data_service.save_fred_data(eu_only)

        latest = {}
        for name, series in eu_only.items():
            if not series.empty:
                last_idx = series.last_valid_index()
                if last_idx is not None:
                    latest[name] = {"date": last_idx.strftime("%Y-%m-%d"), "value": float(series[last_idx])}

        eu_m3 = latest.get("eu_3m", TreasuryData(date=latest_end.date(), value=None))
        eu_y2 = latest.get("eu_2y_ecb", TreasuryData(date=latest_end.date(), value=None))
        eu_y10 = latest.get("eu_10y", TreasuryData(date=latest_end.date(), value=None))

        response_data = EUTreasuriesUpdateData(
            eu_treasuries=EUTreasuries(m3=eu_m3, y2=eu_y2, y10=eu_y10)
        )

        logger.info("欧洲国债历史数据获取成功")
        return UpdateResponse(
            success=True,
            message="欧洲国债历史数据获取成功",
            data=response_data,
            updated_at=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"获取欧洲国债历史数据失败: {str(e)}")
        return UpdateResponse(
            success=False,
            message=f"获取欧洲国债历史数据失败: {str(e)}",
            error_code="UPDATE_FAILED"
        )
    finally:
        release_update_lock()


@router.post("/update/eu-bonds", response_model=UpdateResponse)
async def update_eu_bonds():
    """更新欧洲国债数据接口 - 增量更新最近 365 天的数据"""
    global _is_updating

    if _is_updating:
        return UpdateResponse(
            success=False,
            message="数据更新正在进行中，请稍后再试",
            error_code="UPDATE_IN_PROGRESS"
        )

    await acquire_update_lock()

    try:
        logger.info("开始增量更新欧洲国债数据...")
        fred_service = get_fred_service()
        data_service = get_data_service()

        latest_end = pd.Timestamp.now().normalize()
        start_date = (latest_end - pd.Timedelta(days=365)).normalize()

        logger.info(f"增量更新欧债数据，从 {start_date} 到 {latest_end}")

        eu_data = await _fetch_oecd_bonds(fred_service, start_date, latest_end)
        eu_only = {k: v for k, v in eu_data.items() if k.startswith("eu_")}

        if not any(not series.empty for series in eu_only.values()):
            raise Exception("未能获取到任何欧债新数据")

        data_service.save_fred_data(eu_only)

        latest = {}
        for name, series in eu_only.items():
            if not series.empty:
                last_idx = series.last_valid_index()
                if last_idx is not None:
                    latest[name] = {"date": last_idx.strftime("%Y-%m-%d"), "value": float(series[last_idx])}

        eu_m3 = latest.get("eu_3m", TreasuryData(date=latest_end.date(), value=None))
        eu_y2 = latest.get("eu_2y_ecb", TreasuryData(date=latest_end.date(), value=None))
        eu_y10 = latest.get("eu_10y", TreasuryData(date=latest_end.date(), value=None))

        response_data = EUTreasuriesUpdateData(
            eu_treasuries=EUTreasuries(m3=eu_m3, y2=eu_y2, y10=eu_y10)
        )

        logger.info("欧洲国债数据增量更新成功")
        return UpdateResponse(
            success=True,
            message="欧洲国债数据增量更新成功",
            data=response_data,
            updated_at=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"欧洲国债数据增量更新失败: {str(e)}")
        return UpdateResponse(
            success=False,
            message=f"欧洲国债数据增量更新失败: {str(e)}",
            error_code="UPDATE_FAILED"
        )
    finally:
        release_update_lock()


@router.post("/fetch/jp-bonds/history", response_model=UpdateResponse)
async def fetch_jp_bonds_history():
    """获取日本国债历史数据接口 - 从 2000 年开始获取全部历史数据"""
    global _is_updating

    if _is_updating:
        return UpdateResponse(
            success=False,
            message="数据更新正在进行中，请稍后再试",
            error_code="UPDATE_IN_PROGRESS"
        )

    await acquire_update_lock()

    try:
        logger.info("开始获取日本国债历史数据...")
        fred_service = get_fred_service()
        data_service = get_data_service()

        latest_end = pd.Timestamp.now().normalize()
        start_date = pd.Timestamp(settings.historical_start_date)

        logger.info(f"获取日债历史数据，从 {start_date} 到 {latest_end}")

        jp_data = await _fetch_oecd_bonds(fred_service, start_date, latest_end)
        jp_only = {k: v for k, v in jp_data.items() if k.startswith("jp_")}

        if not any(not series.empty for series in jp_only.values()):
            raise Exception("未能获取到任何日债数据")

        data_service.save_fred_data(jp_only)

        latest = {}
        for name, series in jp_only.items():
            if not series.empty:
                last_idx = series.last_valid_index()
                if last_idx is not None:
                    latest[name] = {"date": last_idx.strftime("%Y-%m-%d"), "value": float(series[last_idx])}

        jp_y10 = latest.get("jp_10y", TreasuryData(date=latest_end.date(), value=None))

        response_data = JPTreasuriesUpdateData(
            jp_treasuries=JPTreasuries(y10=jp_y10)
        )

        logger.info("日本国债历史数据获取成功")
        return UpdateResponse(
            success=True,
            message="日本国债历史数据获取成功",
            data=response_data,
            updated_at=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"获取日本国债历史数据失败: {str(e)}")
        return UpdateResponse(
            success=False,
            message=f"获取日本国债历史数据失败: {str(e)}",
            error_code="UPDATE_FAILED"
        )
    finally:
        release_update_lock()


@router.post("/update/jp-bonds", response_model=UpdateResponse)
async def update_jp_bonds():
    """更新日本国债数据接口 - 增量更新最近 365 天的数据"""
    global _is_updating

    if _is_updating:
        return UpdateResponse(
            success=False,
            message="数据更新正在进行中，请稍后再试",
            error_code="UPDATE_IN_PROGRESS"
        )

    await acquire_update_lock()

    try:
        logger.info("开始增量更新日本国债数据...")
        fred_service = get_fred_service()
        data_service = get_data_service()

        latest_end = pd.Timestamp.now().normalize()
        start_date = (latest_end - pd.Timedelta(days=365)).normalize()

        logger.info(f"增量更新日债数据，从 {start_date} 到 {latest_end}")

        jp_data = await _fetch_oecd_bonds(fred_service, start_date, latest_end)
        jp_only = {k: v for k, v in jp_data.items() if k.startswith("jp_")}

        if not any(not series.empty for series in jp_only.values()):
            raise Exception("未能获取到任何日债新数据")

        data_service.save_fred_data(jp_only)

        latest = {}
        for name, series in jp_only.items():
            if not series.empty:
                last_idx = series.last_valid_index()
                if last_idx is not None:
                    latest[name] = {"date": last_idx.strftime("%Y-%m-%d"), "value": float(series[last_idx])}

        jp_y10 = latest.get("jp_10y", TreasuryData(date=latest_end.date(), value=None))

        response_data = JPTreasuriesUpdateData(
            jp_treasuries=JPTreasuries(y10=jp_y10)
        )

        logger.info("日本国债数据增量更新成功")
        return UpdateResponse(
            success=True,
            message="日本国债数据增量更新成功",
            data=response_data,
            updated_at=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"日本国债数据增量更新失败: {str(e)}")
        return UpdateResponse(
            success=False,
            message=f"日本国债数据增量更新失败: {str(e)}",
            error_code="UPDATE_FAILED"
        )
    finally:
        release_update_lock()

@router.post("/update", response_model=UpdateResponse)
async def update_data():
    """更新数据接口 - n8n 调用此接口触发数据更新（美债 + OECD债券 + 汇率）"""
    global _is_updating

    # 检查是否正在更新
    if _is_updating:
        return UpdateResponse(
            success=False,
            message="数据更新正在进行中，请稍后再试",
            error_code="UPDATE_IN_PROGRESS"
        )

    await acquire_update_lock()

    try:
        logger.info("开始更新数据...")
        fred_service = get_fred_service()
        data_service = get_data_service()

        latest_end = pd.Timestamp.now().normalize()

        # 检查美债数据的最后日期
        us_last_date = data_service.get_last_date("us_treasuries")
        if us_last_date is None:
            # 首次获取，从 2000 年开始
            us_start = pd.Timestamp(settings.historical_start_date)
            logger.info(f"首次获取美债历史数据，从 {us_start} 到 {latest_end}")
        else:
            # 增量更新，获取最近 7 天
            us_start = (latest_end - pd.Timedelta(days=7)).normalize()
            logger.info(f"增量更新美债数据，从 {us_start} 到 {latest_end}")

        # OECD 数据使用 365 天范围
        oecd_start = (latest_end - pd.Timedelta(days=365)).normalize()
        logger.info(f"获取 OECD 债券数据范围: {oecd_start} 到 {latest_end}")

        # 汇率数据也使用增量更新策略
        er_last_date = data_service.get_last_date("exchange_rates")
        if er_last_date is None:
            # 首次获取，从 2000 年开始
            er_start = pd.Timestamp(settings.historical_start_date)
            logger.info(f"首次获取汇率历史数据，从 {er_start} 到 {latest_end}")
        else:
            # 增量更新，获取最近 7 天
            er_start = (latest_end - pd.Timedelta(days=7)).normalize()
            logger.info(f"增量更新汇率数据，从 {er_start} 到 {latest_end}")

        new_data = {}
        exchange_data = {}

        # 获取美国国债数据（3m, 2y, 10y）
        us_data = await _fetch_us_treasuries(fred_service, us_start, latest_end)
        new_data.update(us_data)

        # 获取 OECD 数据（德国、日本 10y）
        oecd_data = await _fetch_oecd_bonds(fred_service, oecd_start, latest_end)
        new_data.update(oecd_data)

        # 获取汇率数据
        exchange_data = await _fetch_exchange_rates(fred_service, er_start, latest_end)

        if not new_data and not exchange_data:
            raise Exception("未能获取到任何新数据")

        # 保存债券数据
        if new_data:
            data_service.save_fred_data(new_data)

        # 保存汇率数据
        if exchange_data:
            data_service.save_fred_data(exchange_data, key="exchange_rates")

        # 构建包含汇率的响应数据
        response_data = _build_response_data_with_rates(new_data, exchange_data, latest_end)

        logger.info("数据更新成功")
        return UpdateResponse(
            success=True,
            message="数据更新成功",
            data=response_data,
            updated_at=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"数据更新失败: {str(e)}")
        return UpdateResponse(
            success=False,
            message=f"数据更新失败: {str(e)}",
            error_code="UPDATE_FAILED"
        )
    finally:
        release_update_lock()


@router.get("/data", response_model=DataResponse)
async def get_data(
    start_date: Optional[str] = Query(None, description="起始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
):
    """查询数据接口 - 前端调用此接口获取展示数据"""
    try:
        logger.info(f"查询数据: start_date={start_date}, end_date={end_date}")
        data_service = get_data_service()

        data = data_service.query_data(start_date, end_date)

        logger.info("数据查询成功")
        return DataResponse(success=True, message="数据查询成功", data=data)

    except Exception as e:
        logger.error(f"数据查询失败: {str(e)}")
        return DataResponse(
            success=False,
            message=f"数据查询失败: {str(e)}",
            error_code="QUERY_FAILED"
        )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查接口"""
    try:
        data_service = get_data_service()

        # 获取最后更新时间
        last_updates = {}
        for data_type in ["us_treasuries", "eu_bonds", "jp_bonds", "exchange_rates", "vix"]:
            last_date = data_service.get_last_date(data_type)
            if last_date:
                last_updates[data_type] = last_date.strftime("%Y-%m-%d")

        # 获取最新的更新时间
        last_update = None
        if last_updates:
            last_update = max(last_updates.values())

        return HealthResponse(
            status="healthy",
            service="global-macro-fin",
            version="1.0.0",
            last_update=last_update,
        )

    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return HealthResponse(
            status="unhealthy",
            service="global-macro-fin",
            version="1.0.0",
            last_update=None,
        )


@router.post("/fetch/vix/history", response_model=UpdateResponse)
async def fetch_vix_history():
    """获取VIX历史数据接口 - 从 2000 年开始获取全部历史数据"""
    global _is_updating

    if _is_updating:
        return UpdateResponse(
            success=False,
            message="数据更新正在进行中，请稍后再试",
            error_code="UPDATE_IN_PROGRESS"
        )

    await acquire_update_lock()

    try:
        logger.info("开始获取VIX历史数据...")
        fred_service = get_fred_service()
        vix_service = get_vix_service()
        data_service = get_data_service()

        latest_end = pd.Timestamp.now().normalize()
        start_date = pd.Timestamp(settings.historical_start_date)

        logger.info(f"获取VIX历史数据，从 {start_date} 到 {latest_end}")

        # 获取VIX数据
        vix_code = settings.fred_codes.get("vix", "VIXCLS")
        vix_series = await fred_service.fetch_series(vix_code, start_date, latest_end)

        if vix_series.empty:
            raise Exception("未能获取到任何VIX数据")

        # 处理VIX数据：时区转换、验证、标准化
        vix_series = vix_service.convert_timezone(vix_series)
        vix_series = vix_service.validate_data(vix_series)
        vix_series = vix_service.normalize_data(vix_series)

        # 保存VIX数据
        vix_data = {"vix": vix_series}
        data_service.save_fred_data(vix_data, key="vix")

        # 构建响应数据
        last_idx = vix_series.last_valid_index()
        vix_latest = VIXData(
            date=last_idx.date() if last_idx is not None else latest_end.date(),
            value=float(vix_series[last_idx]) if last_idx is not None else None
        )

        response_data = VIXUpdateData(vix=vix_latest)

        logger.info("VIX历史数据获取成功")
        return UpdateResponse(
            success=True,
            message="VIX历史数据获取成功",
            data=response_data,
            updated_at=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"获取VIX历史数据失败: {str(e)}")
        return UpdateResponse(
            success=False,
            message=f"获取VIX历史数据失败: {str(e)}",
            error_code="UPDATE_FAILED"
        )
    finally:
        release_update_lock()


@router.post("/update/vix", response_model=UpdateResponse)
async def update_vix():
    """更新VIX数据接口 - 增量更新最近 7 天的数据"""
    global _is_updating

    if _is_updating:
        return UpdateResponse(
            success=False,
            message="数据更新正在进行中，请稍后再试",
            error_code="UPDATE_IN_PROGRESS"
        )

    await acquire_update_lock()

    try:
        logger.info("开始增量更新VIX数据...")
        fred_service = get_fred_service()
        vix_service = get_vix_service()
        data_service = get_data_service()

        latest_end = pd.Timestamp.now().normalize()
        start_date = (latest_end - pd.Timedelta(days=7)).normalize()

        logger.info(f"增量更新VIX数据，从 {start_date} 到 {latest_end}")

        # 获取VIX数据
        vix_code = settings.fred_codes.get("vix", "VIXCLS")
        vix_series = await fred_service.fetch_series(vix_code, start_date, latest_end)

        if vix_series.empty:
            raise Exception("未能获取到任何VIX新数据")

        # 处理VIX数据：时区转换、验证、标准化
        vix_series = vix_service.convert_timezone(vix_series)
        vix_series = vix_service.validate_data(vix_series)
        vix_series = vix_service.normalize_data(vix_series)

        # 保存VIX数据
        vix_data = {"vix": vix_series}
        data_service.save_fred_data(vix_data, key="vix")

        # 构建响应数据
        last_idx = vix_series.last_valid_index()
        vix_latest = VIXData(
            date=last_idx.date() if last_idx is not None else latest_end.date(),
            value=float(vix_series[last_idx]) if last_idx is not None else None
        )

        response_data = VIXUpdateData(vix=vix_latest)

        logger.info("VIX数据增量更新成功")
        return UpdateResponse(
            success=True,
            message="VIX数据增量更新成功",
            data=response_data,
            updated_at=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"VIX数据增量更新失败: {str(e)}")
        return UpdateResponse(
            success=False,
            message=f"VIX数据增量更新失败: {str(e)}",
            error_code="UPDATE_FAILED"
        )
    finally:
        release_update_lock()
