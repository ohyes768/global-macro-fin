#!/bin/bash
# 停止脚本

echo "=========================================="
echo "停止 Global Macro Finance 服务"
echo "=========================================="

# 查找并停止进程
PID=$(lsof -ti:8094)

if [ -n "$PID" ]; then
    echo "停止服务 (PID: $PID)..."
    kill -15 "$PID"
    sleep 2

    # 检查是否停止成功
    if lsof -ti:8094 > /dev/null 2>&1; then
        echo "强制停止服务..."
        kill -9 "$PID"
    fi

    echo "服务已停止"
else
    echo "服务未运行"
fi
