"""解析 ECB 数据流 XML 文件"""
# -*- coding: utf-8 -*-
import xml.etree.ElementTree as ET
import sys

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 读取 XML 文件
with open("ecb_dataflows.xml", "r", encoding="utf-8") as f:
    content = f.read()

# 尝试解析
try:
    root = ET.fromstring(content)

    # 打印根元素信息
    print(f"根元素: {root.tag}")

    # 递归查找所有包含 id 属性的元素
    print("\n所有带 id 属性的元素:")
    for elem in root.iter():
        elem_id = elem.get('id')
        if elem_id:
            name = elem.get('name', '')
            # 打印所有数据流
            print(f"  id={elem_id}, name={name[:80] if name else '(no name)'}")

except Exception as e:
    print(f"解析失败: {e}")

    # 尝试手动搜索 id 属性
    import re
    print("\n使用正则表达式搜索 id 属性:")
    pattern = r'id="([^"]+)"'
    ids = re.findall(pattern, content)
    print(f"找到 {len(ids)} 个 id:")
    for id_val in sorted(set(ids))[:50]:  # 显示前50个唯一ID
        print(f"  - {id_val}")
