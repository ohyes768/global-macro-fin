#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 FRED API 获取 SOFR 和 DGS3MO 数据并计算利差
"""
import os
import sys
import pandas as pd
from fredapi import Fred
from dotenv import load_dotenv

# 修复 Windows 控制台编码问题
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()

def test_fred_sofr_spread():
    """测试获取 SOFR 和 DGS3MO 数据并计算利差"""

    # 初始化 FRED API（使用环境变量或硬编码测试）
    fred_api_key = os.getenv('FRED_API_KEY')

    if not fred_api_key:
        print("ERROR: FRED_API_KEY not found")
        print("Please set FRED_API_KEY or register at: https://fred.stlouisfed.org/docs/api/api_key.html")
        return False

    fred = Fred(api_key=fred_api_key)

    print("=" * 60)
    print("Starting FRED API Data Test")
    print("=" * 60)

    # 1. 获取 SOFR 数据
    print("\n[1/4] Fetching SOFR data...")
    try:
        sofr_data = fred.get_series('SOFR', observation_start='2025-01-01')
        print(f"OK: SOFR data fetched, {len(sofr_data)} points")
        print(f"   Last 5 values:")
        print(f"   {sofr_data.tail()}")
    except Exception as e:
        print(f"ERROR: Failed to fetch SOFR: {e}")
        return False

    # 2. 获取 DGS3MO 数据
    print("\n[2/4] Fetching DGS3MO data...")
    try:
        dgs3mo_data = fred.get_series('DGS3MO', observation_start='2025-01-01')
        print(f"OK: DGS3MO data fetched, {len(dgs3mo_data)} points")
        print(f"   Last 5 values:")
        print(f"   {dgs3mo_data.tail()}")
    except Exception as e:
        print(f"ERROR: Failed to fetch DGS3MO: {e}")
        return False

    # 3. 合并数据并计算利差
    print("\n[3/4] Calculating spread...")
    df = pd.DataFrame({
        'SOFR': sofr_data,
        'DGS3MO': dgs3mo_data
    })

    # 移除空值
    df_clean = df.dropna()

    if len(df_clean) == 0:
        print("ERROR: No valid overlapping data")
        return False

    # 计算利差
    df_clean['Spread'] = df_clean['SOFR'] - df_clean['DGS3MO']
    df_clean['Spread_BPS'] = df_clean['Spread'] * 100  # 转换为基点

    print(f"OK: Spread calculated, {len(df_clean)} valid points")
    print(f"\n   Recent spread data:")
    print(f"   {df_clean[['SOFR', 'DGS3MO', 'Spread', 'Spread_BPS']].tail()}")
    print(f"\n   Spread statistics:")
    print(f"   Mean: {df_clean['Spread_BPS'].mean():.2f} bps")
    print(f"   Min: {df_clean['Spread_BPS'].min():.2f} bps")
    print(f"   Max: {df_clean['Spread_BPS'].max():.2f} bps")
    print(f"   Std: {df_clean['Spread_BPS'].std():.2f} bps")

    # 4. 保存到 CSV
    output_file = 'sofr_spread_test.csv'
    df_clean.to_csv(output_file)
    print(f"\n[4/4] Data saved to: {output_file}")

    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)

    return True

if __name__ == '__main__':
    test_fred_sofr_spread()