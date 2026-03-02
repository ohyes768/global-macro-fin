"""API 路由模块"""
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
import pandas as pd
from typing import Optional

from src.models import UpdateResponse, DataResponse, HealthResponse, MacroData, TreasuryData, USTreasuries
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


@router.post("/api/update", response_model=UpdateResponse)
async def update_data():
    """更新数据接口 - n8n 调用此接口触发数据更新"""
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

        # 获取需要更新的时间范围
        end = pd.Timestamp.now().normalize() - pd.Timedelta(days=1)

        # 检查各数据源的最后日期
        start_dates = {}
        for data_type in ["us_treasuries", "eu_bonds", "jp_bonds"]:
            last_date = data_service.get_last_date(data_type)
            if last_date is None:
                # 首次获取，从历史起始日期开始
                start_dates[data_type] = pd.Timestamp(settings.historical_start_date)
            else:
                # 增量更新，从最后日期的下一天开始
                start_dates[data_type] = last_date + pd.Timedelta(days=1)

        # 获取最新数据（使用最近的时间范围，确保获取到数据）
        latest_end = pd.Timestamp.now().normalize()
        latest_start = (latest_end - pd.Timedelta(days=7)).normalize()

        logger.info(f"获取数据范围: {latest_start} 到 {latest_end}")
        new_data = await fred_service.fetch_all_treasuries(latest_start, latest_end)

        if not new_data:
            raise Exception("未能获取到任何新数据")

        # 保存数据
        data_service.save_fred_data(new_data)

        # 构建响应数据
        response_data = None
        if new_data:
            # 获取最新数据点
            latest = {}
            for name, series in new_data.items():
                if not series.empty:
                    last_idx = series.last_valid_index()
                    if last_idx is not None:
                        latest[name] = {"date": last_idx.strftime("%Y-%m-%d"), "value": float(series[last_idx])}

            # 构建响应
            us_m3 = latest.get("us_3m", TreasuryData(date=end.date(), value=None))
            us_y2 = latest.get("us_2y", TreasuryData(date=end.date(), value=None))
            us_y10 = latest.get("us_10y", TreasuryData(date=end.date(), value=None))
            eu_10y = latest.get("eu_10y", TreasuryData(date=end.date(), value=None))
            jp_10y = latest.get("jp_10y", TreasuryData(date=end.date(), value=None))

            response_data = MacroData(
                us_treasuries=USTreasuries(m3=us_m3, y2=us_y2, y10=us_y10),
                eu_10y=eu_10y,
                jp_10y=jp_10y,
            )

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
