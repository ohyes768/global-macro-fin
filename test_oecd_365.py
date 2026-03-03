"""测试 OECD 数据在 365 天范围内是否可用"""
import pandas as pd
from fredapi import Fred
from datetime import datetime

# FRED API 配置
api_key = '8ecbb41e142454c0ce3ada51ebb489a8'
fred = Fred(api_key=api_key)

# OECD 数据代码
oecd_codes = {
    "Germany 10Y": "IRLTLT01DEM156N",
    "Japan 10Y": "IRLTLT01JPM156N"
}

# 计算 365 天前的日期
end_date = pd.Timestamp.now().normalize()
start_date = (end_date - pd.Timedelta(days=365)).normalize()

print(f"测试日期范围: {start_date} 到 {end_date}")
print(f"即 {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
print()

for name, code in oecd_codes.items():
    print(f"正在获取 {name} ({code})...")
    try:
        data = fred.get_series(code, observation_start=start_date, observation_end=end_date)
        if not data.empty:
            print(f"  成功! 获取到 {len(data)} 条记录")
            print(f"  最新数据: {data.index[-1].strftime('%Y-%m-%d')} = {data.iloc[-1]}")
            print(f"  最早数据: {data.index[0].strftime('%Y-%m-%d')} = {data.iloc[0]}")
        else:
            print(f"  失败! 数据为空")
    except Exception as e:
        print(f"  错误: {e}")
    print()
