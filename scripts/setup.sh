#!/bin/bash
# 环境设置脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR" || exit 1

echo "=========================================="
echo "设置 Global Macro Finance 开发环境"
echo "=========================================="

# 检查 uv 是否安装
if ! command -v uv &> /dev/null; then
    echo "错误: uv 未安装，请先安装 uv"
    echo "安装命令: pip install uv"
    exit 1
fi

# 创建虚拟环境
echo "创建虚拟环境..."
uv venv .venv

# 激活虚拟环境并安装依赖
echo "安装依赖..."
source .venv/bin/activate
uv pip install -e .

# 创建环境变量文件
if [ ! -f ".env" ]; then
    echo "创建 .env 文件..."
    cp .env.example .env
    echo "请编辑 .env 文件，设置 FRED_API_KEY"
fi

# 创建必要的目录
mkdir -p data logs

echo "=========================================="
echo "环境设置完成！"
echo "=========================================="
echo "请编辑 .env 文件，设置 FRED_API_KEY"
echo "然后运行 ./scripts/start.sh 启动服务"
