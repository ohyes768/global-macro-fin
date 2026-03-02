# Global Macro Finance

全球宏观经济债券利率数据服务

## 功能

- 获取美债、欧债、日债利率数据
- 提供 API 接口供 n8n 和前端调用
- 支持历史数据查询
- 自动数据更新和重试机制

## API 接口

### POST /api/update
n8n 调用此接口触发数据更新

```bash
curl -X POST http://localhost:8094/api/update
```

### GET /api/data
查询历史数据

```bash
curl "http://localhost:8094/api/data?start_date=2024-01-01&end_date=2024-12-31"
```

### GET /api/health
健康检查

```bash
curl http://localhost:8094/api/health
```

## 开发

### 环境设置

```bash
cd scripts
./setup.sh
```

### 配置环境变量

编辑 `.env` 文件：

```bash
FRED_API_KEY=your_fred_api_key_here
```

### 启动服务

```bash
cd scripts
./start.sh
```

### 停止服务

```bash
cd scripts
./stop.sh
```

## Docker 部署

### 构建镜像

```bash
docker build -t global-macro-fin .
```

### 运行容器

```bash
docker run -d \
  --name global-macro-fin \
  -p 8094:8094 \
  -e FRED_API_KEY=your_key \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  global-macro-fin
```

## 技术栈

- Python 3.12
- FastAPI
- pandas
- fredapi
