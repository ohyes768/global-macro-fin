"""测试路由模块是否正确加载"""
import sys
sys.path.insert(0, '.')

# 检查 api_routes.py 中的关键代码
with open('src/api/routes.py', 'r', encoding='utf-8') as f:
    content = f.read()
    if '获取美国国债数据范围' in content:
        print("[OK] File contains new log message")
    else:
        print("[FAIL] File does not contain new log message")
        sys.exit(1)

    if 'oecd_start' in content:
        print("[OK] File contains oecd_start variable")
    else:
        print("[FAIL] File does not contain oecd_start variable")
        sys.exit(1)

# 尝试导入模块
try:
    from src.api import routes
    print("[OK] Successfully imported routes module")
except Exception as e:
    print(f"[FAIL] Import failed: {e}")
    sys.exit(1)

# 检查函数签名
import inspect
source = inspect.getsource(routes.update_data)
if 'oecd_start' in source:
    print("[OK] update_data function contains new code")
else:
    print("[FAIL] update_data function does not contain new code")
    print(f"Function source:\n{source}")
    sys.exit(1)

print("\nAll checks passed! Code changes are correctly loaded.")
