# Global Macro Finance API 文档

## 基础信息

| 项目 | 值 |
|------|-----|
| 服务名称 | Global Macro Finance API |
| 基础路径 | `http://localhost:8094` |
| API 文档 | `/docs` (Swagger UI) |
| 版本 | 1.0.0 |

---

## 1. 获取美国国债历史数据

### 接口
`POST /api/fetch/us-treasuries/history`

### 说明
获取从 2000 年开始的全部美国国债历史数据（3m, 2y, 10y）

### 行为逻辑
- 从 2000-01-01 开始获取全部历史数据
- 首次部署或需要重建数据时使用
- 响应时间较长（约 30-40 秒）

### 请求示例
```bash
curl -X POST http://localhost:8094/api/fetch/us-treasuries/history
```

### 响应示例
```json
{
  "success": true,
  "message": "美国国债历史数据获取成功",
  "data": {
    "us_treasuries": {
      "m3": {"date": "2026-02-27", "value": 3.67},
      "y2": {"date": "2026-02-27", "value": 3.38},
      "y10": {"date": "2026-02-27", "value": 3.97}
    }
  },
  "updated_at": "2026-03-03T13:27:12.126340",
  "error_code": null
}
```

---

## 2. 更新美国国债数据

### 接口
`POST /api/update/us-treasuries`

### 说明
增量更新美国国债数据（最近 7 天）

### 行为逻辑
- 获取最近 7 天的数据
- 用于定时更新（如 n8n 每日调用）
- 响应时间短（约 3-5 秒）

### 请求示例
```bash
curl -X POST http://localhost:8094/api/update/us-treasuries
```

### 响应示例
```json
{
  "success": true,
  "message": "美国国债数据增量更新成功",
  "data": {
    "us_treasuries": {
      "m3": {"date": "2026-02-27", "value": 3.67},
      "y2": {"date": "2026-02-27", "value": 3.38},
      "y10": {"date": "2026-02-27", "value": 3.97}
    }
  },
  "updated_at": "2026-03-03T13:26:46.978788",
  "error_code": null
}
```

---

## 3. 更新全部数据

### 接口
`POST /api/update`

### 说明
更新所有数据（美国国债 + OECD债券）

### 行为逻辑
- **美债数据**: 增量更新最近 7 天
- **OECD 债券**（德国、日本 10y）: 获取最近 365 天的数据（月度数据）

### 请求示例
```bash
curl -X POST http://localhost:8094/api/update
```

### 响应示例
```json
{
  "success": true,
  "message": "数据更新成功",
  "data": {
    "us_treasuries": {
      "m3": {"date": "2026-02-27", "value": 3.67},
      "y2": {"date": "2026-02-27", "value": 3.38},
      "y10": {"date": "2026-02-27", "value": 3.97}
    },
    "eu_10y": {"date": "2026-01-01", "value": 2.81},
    "jp_10y": {"date": "2026-01-01", "value": 2.24}
  },
  "updated_at": "2026-03-03T10:41:20.243868",
  "error_code": null
}
```

---

## 4. 查询数据

### 接口
`GET /api/data`

### 说明
前端调用此接口获取展示数据

### 查询参数

| 参数 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `start_date` | string | 否 | 起始日期 (YYYY-MM-DD) | `2000-01-01` |
| `end_date` | string | 否 | 结束日期 (YYYY-MM-DD) | `2025-12-31` |

### 默认行为
如果不传参数，返回最近 90 天的数据

### 请求示例
```bash
# 查询从 2000 年至今的所有数据
curl "http://localhost:8094/api/data?start_date=2000-01-01"

# 查询指定范围
curl "http://localhost:8094/api/data?start_date=2020-01-01&end_date=2025-12-31"

# 查询最近 90 天（默认）
curl "http://localhost:8094/api/data"
```

### 响应示例
```json
{
  "success": true,
  "message": "数据查询成功",
  "data": {
    "dates": ["2000-01-03", "2000-01-04", "2000-01-05", ...],
    "us_treasuries": {
      "3m": [5.48, 5.43, 5.44, ...],
      "2y": [6.38, 6.30, 6.38, ...],
      "10y": [6.58, 6.49, 6.62, ...]
    },
    "eu_10y": [null, null, ..., 2.81],
    "jp_10y": [null, null, ..., 2.24]
  },
  "error_code": null
}
```

### 数据说明
- `dates`: 日期数组，所有数据共享同一时间轴
- `us_treasuries`: 美国国债收益率数据
- `eu_10y`: 德国 10 年期国债收益率（月度数据，早期可能为空）
- `jp_10y`: 日本 10 年期国债收益率（月度数据，早期可能为空）

---

## 5. 健康检查

### 接口
`GET /api/health`

### 请求示例
```bash
curl http://localhost:8094/api/health
```

### 响应示例
```json
{
  "status": "healthy",
  "service": "global-macro-fin",
  "version": "1.0.0",
  "last_update": "2026-02-27"
}
```

---

## 数据源说明

| 数据类型 | FRED 代码 | 频率 | 历史起始 |
|---------|-----------|------|---------|
| 美债 3m | `DGS3MO` | 每日 | 2000-01-01 |
| 美债 2y | `DGS2` | 每日 | 2000-01-01 |
| 美债 10y | `DGS10` | 每日 | 2000-01-01 |
| 德债 10y | `IRLTLT01DEM156N` | 月度 | 约 2000 年后 |
| 日债 10y | `IRLTLT01JPM156N` | 月度 | 约 2000 年后 |

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| `UPDATE_IN_PROGRESS` | 数据更新正在进行中 |
| `UPDATE_FAILED` | 数据更新失败 |
| `QUERY_FAILED` | 数据查询失败 |

---

## 并发控制

所有更新接口使用全局锁，同一时间只能有一个更新任务在执行。

---

## 使用场景

| 场景 | 使用接口 | 频率 |
|------|----------|------|
| 首次部署/初始化 | `POST /api/fetch/us-treasuries/history` | 一次性 |
| 定时更新（n8n） | `POST /api/update/us-treasuries` | 每日 |
| 完整更新（含 OECD） | `POST /api/update` | 按需 |
| 前端展示 | `GET /api/data` | 实时 |
| 健康检查 | `GET /api/health` | 监控 |
