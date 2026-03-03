"""API 路由模块"""
print("[INIT-20260303-0942] routes.py 模块已加载")
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
import pandas as pd
from typing import Optional

from src.models import UpdateResponse, DataResponse, HealthResponse, MacroData, TreasuryData, USTreasuries, USTreasuriesUpdateData
from src.services.fred_service import get_fred_service
from src.services.data_service import get_data_service
from src.utils.logger import setup_logger
from src.config import get_settings

logger = setup_logger("api_routes")
settings = get_settings()

router = APIRouter()

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
    oecd_codes = {"eu_10y", "jp_10y"}

    for name in oecd_codes:
        code = settings.fred_codes[name]
        try:
            series = await fred_service.fetch_series(code, start_date, end_date)
            oecd_data[name] = series
        except Exception as e:
            logger.error(f"获取 {name} ({code}) 数据时出错: {e}")
            oecd_data[name] = pd.Series(dtype="float64")

    return oecd_data


def _build_response_data(new_data: dict, end_date: pd.Timestamp) -> MacroData:
    """构建响应数据的内部函数

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
    eu_10y = latest.get("eu_10y", TreasuryData(date=end_date.date(), value=None))
    jp_10y = latest.get("jp_10y", TreasuryData(date=end_date.date(), value=None))

    return MacroData(
        us_treasuries=USTreasuries(m3=us_m3, y2=us_y2, y10=us_y10),
        eu_10y=eu_10y,
        jp_10y=jp_10y,
    )


@router.post("/api/fetch/us-treasuries/history", response_model=UpdateResponse)
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


@router.post("/api/update/us-treasuries", response_model=UpdateResponse)
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


@router.post("/api/update", response_model=UpdateResponse)
async def update_data():
    """更新数据接口 - n8n 调用此接口触发数据更新（美债 + OECD债券）"""
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

        new_data = {}

        # 获取美国国债数据（3m, 2y, 10y）
        us_data = await _fetch_us_treasuries(fred_service, us_start, latest_end)
        new_data.update(us_data)

        # 获取 OECD 数据（德国、日本 10y）
        oecd_data = await _fetch_oecd_bonds(fred_service, oecd_start, latest_end)
        new_data.update(oecd_data)

        if not new_data:
            raise Exception("未能获取到任何新数据")

        # 保存数据
        data_service.save_fred_data(new_data)

        response_data = _build_response_data(new_data, latest_end)

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


@router.get("/api/data", response_model=DataResponse)
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


@router.get("/api/health", response_model=HealthResponse)
async def health_check():
    """健康检查接口"""
    try:
        data_service = get_data_service()

        # 获取最后更新时间
        last_updates = {}
        for data_type in ["us_treasuries", "eu_bonds", "jp_bonds"]:
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
