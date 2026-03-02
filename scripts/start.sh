#!/bin/bash
# 启动脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR" || exit 1

echo "=========================================="
echo "启动 Global Macro Finance 服务"
echo "=========================================="

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "错误: 虚拟环境不存在，请先运行 setup.sh"
    exit 1
fi

# 激活虚拟环境
source .venv/bin/activate

# 检查环境变量文件
if [ ! -f ".env" ]; then
    echo "警告: .env 文件不存在，从 .env.example 复制..."
    cp .env.example .env
    echo "请编辑 .env 文件，设置 FRED_API_KEY"
    exit 1
fi

# 创建必要的目录
mkdir -p data logs

# 启动服务
echo "启动服务..."
python -m uvicorn src.main:app --host 0.0.0.0 --port 8094 --reload
