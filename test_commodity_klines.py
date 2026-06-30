#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 commodity_service：comkm K 线拉取 + 服务端单位换算 + sanity check

手动测试脚本（项目惯例，参考 test_fred_sofr.py），不引入 pytest 框架。

覆盖 case：
1. unit_conversion_copper — USHG $/磅 → service ×2204.62 = $/吨
2. unit_conversion_silver — SGEAG9999 元/千克 → service ÷1000 = 元/克
3. pagination — fetch_klines 翻页逻辑：page1=500、page2=500、page3=123
4. sanity_check_warns_on_extreme — gold 越界 → log warn（不抛异常）
"""
import asyncio
import io
import logging
import sys
from datetime import date
from unittest.mock import AsyncMock, patch

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import httpx
import pandas as pd

from src.config import get_settings
from src.services.commodity_service import (
    AliyunCommodityKlineClient,
    CommodityService,
)


# ------------------------- 测试函数 -------------------------

async def test_unit_conversion_copper():
    """USHG 铜：comkm 返回 close=4.50 ($/磅)，service 应换算为 ≈9920.79 $/吨

    公式：factor = 2204.62 (磅→吨)
    """
    settings = get_settings()
    fake_records = [
        {"date": pd.Timestamp("2024-06-15"), "close": 4.50},
    ]

    # patch AliyunCommodityKlineClient.fetch_klines 让其返回伪造 records，
    # 跳过 __aenter__/__aexit__ 创建真实 httpx 连接
    with patch.object(
        AliyunCommodityKlineClient, "fetch_klines",
        new=AsyncMock(return_value=fake_records),
    ):
        result = await CommodityService.fetch_all(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

    assert "copper" in result, "commodity_service.fetch_all 应返回 copper"
    assert not result["copper"].empty, "copper series 不应为空"

    actual = float(result["copper"].iloc[0])
    expected = 4.50 * settings.commodity_units["copper"]["factor"]
    assert abs(actual - expected) < 0.01, f"got {actual}, expected {expected}"

    print(f"  OK copper: comkm raw=4.50 × {settings.commodity_units['copper']['factor']} "
          f"= {actual:.2f} {settings.commodity_units['copper']['display']} "
          f"(预期 {expected:.2f})")
    return True


async def test_unit_conversion_silver():
    """SGEAG9999 白银：comkm 返回 close=14500 (元/千克)，service 应换算为 ≈14.50 元/克

    公式：factor = 0.001 (元/千克 → 元/克)
    """
    settings = get_settings()
    fake_records = [
        {"date": pd.Timestamp("2024-06-15"), "close": 14500.0},
    ]

    with patch.object(
        AliyunCommodityKlineClient, "fetch_klines",
        new=AsyncMock(return_value=fake_records),
    ):
        result = await CommodityService.fetch_all(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )

    assert "silver" in result, "应返回 silver"
    assert not result["silver"].empty, "silver series 不应为空"

    actual = float(result["silver"].iloc[0])
    expected = 14500.0 * settings.commodity_units["silver"]["factor"]
    assert abs(actual - expected) < 0.01, f"got {actual}, expected {expected}"

    print(f"  OK silver: comkm raw=14500 × {settings.commodity_units['silver']['factor']} "
          f"= {actual:.3f} {settings.commodity_units['silver']['display']} "
          f"(预期 {expected:.3f})")
    return True


async def test_pagination():
    """验证 AliyunCommodityKlineClient.fetch_klines 的翻页终止逻辑：
    page1=500 条、page2=500 条、page3=123 条（不足一页） → 共 1123 条，3 次 HTTP 调用
    """
    calls: list = []

    def make_page(pidx: int) -> list:
        # 三页日期不重叠
        if pidx == 1:
            return [
                {"C": float(i), "D": f"2024-01-{(i % 28) + 1:02d} 00:00:00"}
                for i in range(1, 501)
            ]
        elif pidx == 2:
            # 跨 2024-01 末 + 2024-02 初
            return [
                {"C": float(i + 500),
                 "D": f"2024-{(1 if i <= 14 else 2):02d}-{(i % 28) + 1:02d} 00:00:00"}
                for i in range(1, 501)
            ]
        else:  # pidx == 3
            return [
                {"C": float(i + 1000),
                 "D": f"2025-{(1 if i <= 14 else 2):02d}-{(i % 28) + 1:02d} 00:00:00"}
                for i in range(1, 124)
            ]

    def handler(request: httpx.Request) -> httpx.Response:
        pidx = int(request.url.params["pidx"])
        symbol = request.url.params["symbol"]
        calls.append((symbol, pidx))
        return httpx.Response(200, json={
            "Code": 0, "Msg": "", "Obj": make_page(pidx),
        })

    transport = httpx.MockTransport(handler)
    settings = get_settings()
    # 直接构造 client_obj 不走 async with，注入 mock transport
    client_obj = AliyunCommodityKlineClient(
        settings.alirmcom_appcode or "test-appcode",
        settings.alirmcom_base_url,
    )
    client_obj._client = httpx.AsyncClient(
        headers=client_obj._headers,
        timeout=30.0,
        transport=transport,
    )

    try:
        records = await client_obj.fetch_klines("TEST_FAKE")
    finally:
        await client_obj._client.aclose()

    assert len(records) == 1123, f"expected 1123 records, got {len(records)}"
    assert len(calls) == 3, f"expected 3 HTTP calls, got {len(calls)}"
    # 验证升序
    dates = [r["date"] for r in records]
    assert dates == sorted(dates), "records 应按日期升序"

    print(f"  OK pagination: {len(records)} records, {len(calls)} HTTP calls, "
          f"first={records[0]['date'].strftime('%Y-%m-%d')}, "
          f"last={records[-1]['date'].strftime('%Y-%m-%d')}")
    return True


async def test_sanity_check_warns_on_extreme():
    """验证 sanity check 越界时 log warn（不抛异常）"""
    settings = get_settings()
    fake_records = [
        # gold 越界 — 元/克 正常范围 100-2000，给 0.001 触发 warn
        {"date": pd.Timestamp("2024-06-15"), "close": 0.001},
    ]

    captured_warnings: list = []

    class ListHandler(logging.Handler):
        def emit(self, record):
            if record.levelno >= logging.WARNING and "sanity" in record.getMessage().lower() or \
               record.levelno >= logging.WARNING and "首行 close" in record.getMessage():
                captured_warnings.append(record.getMessage())

    handler = ListHandler()
    logger = logging.getLogger("commodity_service")
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)
    try:
        with patch.object(
            AliyunCommodityKlineClient, "fetch_klines",
            new=AsyncMock(return_value=fake_records),
        ):
            result = await CommodityService.fetch_all(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
            )
    finally:
        logger.removeHandler(handler)

    assert "gold" in result, "应返回 gold"
    assert not result["gold"].empty, "gold series 不应为空"
    assert any("gold" in msg and "超出预期范围" in msg for msg in captured_warnings), \
        f"应至少有一条 gold 越界 warn，实际: {captured_warnings}"

    print(f"  OK sanity warn: gold=0.001 触发 {len(captured_warnings)} 条 warn")
    return True


# ------------------------- main -------------------------

async def main():
    tests = [
        ("unit_conversion_copper", test_unit_conversion_copper),
        ("unit_conversion_silver", test_unit_conversion_silver),
        ("pagination", test_pagination),
        ("sanity_check_warns_on_extreme", test_sanity_check_warns_on_extreme),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        print(f"\n[TEST] {name}")
        try:
            ok = await fn()
            if ok:
                passed += 1
            else:
                print(f"  FAIL: {name} 返回 False")
                failed += 1
        except Exception as e:
            print(f"  FAIL: {name} 抛异常: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"PASSED: {passed}/{len(tests)}")
    print(f"FAILED: {failed}/{len(tests)}")
    print(f"{'='*60}")
    return failed == 0


if __name__ == "__main__":
    ok = asyncio.run(main())
    sys.exit(0 if ok else 1)
