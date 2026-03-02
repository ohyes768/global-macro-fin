FROM python:3.12-slim

WORKDIR /app

# 安装 uv
RUN pip install --no-cache-dir uv

# 复制项目配置
COPY pyproject.toml ./

# 创建虚拟环境并安装依赖
RUN uv venv .venv
RUN .venv/bin/pip install --no-cache-dir -e .

# 复制源代码
COPY src/ ./src/

# 创建必要的目录
RUN mkdir -p data logs

# 暴露端口
EXPOSE 8094

# 启动命令
CMD [".venv/bin/uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8094"]
