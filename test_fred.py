"""测试 FRED API 代码"""
from fredapi import Fred

fred = Fred(api_key='8ecbb41e142454c0ce3ada51ebb489a8')

print("Testing Germany 10Y...")
try:
    data = fred.get_series('IRLTLT01DEM156N')
    print(f"Germany 10Y OK! Last value: {data.iloc[-1]}")
except Exception as e:
    print(f"Germany 10Y Failed: {e}")

print("\nTesting Japan 10Y...")
try:
    data = fred.get_series('IRLTLT01JPM156N')
    print(f"Japan 10Y OK! Last value: {data.iloc[-1]}")
except Exception as e:
    print(f"Japan 10Y Failed: {e}")
