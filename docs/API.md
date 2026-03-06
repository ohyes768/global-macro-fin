# 后端 API 接口文档

本文档描述了后端所有服务的 API 接口规范。

---

## 服务架构

| 服务名称 | 端口 | 说明 |
|---------|------|------|
| douyin-processor | 8093 | 抖音视频处理服务 |
| global-macro-fin | 8094 | 宏观经济数据服务 |

---

## 一、douyin-processor (抖音视频处理服务)

**服务地址**: `http://localhost:8093`

**基础路径**: 无

---

### 1. 根路径

获取服务信息。

**请求**

| 属性 | 值 |
|------|-----|
| 方法 | GET |
| 路径 | `/` |

**响应示例**

```json
{
  "service": "douyin-processor",
  "version": "1.0.0",
  "docs": "/docs",
  "health": "/health"
}
```

---

### 2. 健康检查

服务健康检查。

**请求**

| 属性 | 值 |
|------|-----|
| 方法 | GET |
| 路径 | `/health` |

**响应示例**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "processor_ready": true
}
```

---

### 3. 异步处理视频

异步处理所有视频，立即返回任务状态，后台继续处理。

**请求**

| 属性 | 值 |
|------|-----|
| 方法 | POST |
| 路径 | `/api/macro/process/async` |

**响应**

```json
{
  "success": true,
  "message": "后台处理任务已启动",
  "data": {
    "total": 10,
    "pending": 5,
    "skip": 5
  }
}
```

---

### 4. 同步处理视频

同步处理所有视频，等待处理完成后返回结果。

**请求**

| 属性 | 值 |
|------|-----|
| 方法 | POST |
| 路径 | `/api/macro/process` |

**响应**

```json
{
  "success": true,
  "message": "处理完成",
  "data": {
    "completed": 5,
    "failed": 1,
    "total": 6
  }
}
```

---

### 5. 获取视频列表

获取视频列表，支持分页和状态筛选。

**请求**

| 属性 | 值 |
|------|-----|
| 方法 | GET |
| 路径 | `/api/macro/videos` |

**查询参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | int | 1 | 页码 |
| page_size | int | 20 | 每页数量（最大100） |
| status | string | - | 状态筛选：completed/processing/failed/pending |
| is_read | bool | - | 是否已读筛选 |

**响应**

```json
{
  "total_count": 10,
  "videos": [
    {
      "aweme_id": "730123456789",
      "status": "completed",
      "title": "视频标题",
      "author": "作者",
      "is_read": false,
      "created_at": "2026-03-05T10:00:00Z",
      "updated_at": "2026-03-05T10:05:00Z"
    }
  ],
  "page": 1,
  "page_size": 20
}
```

---

### 6. 获取视频详情

获取单个视频的详细信息。

**请求**

| 属性 | 值 |
|------|-----|
| 方法 | GET |
| 路径 | `/api/macro/videos/{aweme_id}` |

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| aweme_id | string | 视频ID |

**响应**

```json
{
  "aweme_id": "730123456789",
  "status": "completed",
  "title": "视频标题",
  "author": "作者",
  "is_read": false,
  "created_at": "2026-03-05T10:00:00Z",
  "updated_at": "2026-03-05T10:05:00Z",
  "transcript": {
    "text": "转录文本内容...",
    "segments": [
      {
        "start": 0,
        "end": 5.2,
        "text": "第一句话"
      }
    ]
  },
  "summary": "视频摘要..."
}
```

---

### 7. 获取视频处理结果

获取视频的处理结果。

**请求**

| 属性 | 值 |
|------|-----|
| 方法 | GET |
| 路径 | `/api/macro/videos/{aweme_id}/result` |

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| aweme_id | string | 视频ID |

**响应**

```json
{
  "aweme_id": "730123456789",
  "status": "completed",
  "result": {
    "transcript": {...},
    "summary": "...",
    "metadata": {...}
  }
}
```

---

### 8. 标记视频已读/未读

标记视频的已读状态。

**请求**

| 属性 | 值 |
|------|-----|
| 方法 | POST |
| 路径 | `/api/macro/videos/{aweme_id}/read` |

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| aweme_id | string | 视频ID |

**请求体**

```json
{
  "is_read": true
}
```

**响应**

```json
{
  "success": true,
  "message": "视频状态已更新"
}
```

---

### 9. 删除视频

硬删除视频，无法恢复。

**请求**

| 属性 | 值 |
|------|-----|
| 方法 | DELETE |
| 路径 | `/api/macro/videos/{aweme_id}` |

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| aweme_id | string | 视频ID |

**响应**

```json
{
  "success": true,
  "message": "视频已完全删除"
}
```

---

### 10. 获取处理统计信息

获取视频处理的统计信息。

**请求**

| 属性 | 值 |
|------|-----|
| 方法 | GET |
| 路径 | `/api/macro/stats` |

**响应**

```json
{
  "total": 10,
  "completed": 5,
  "processing": 1,
  "failed": 1,
  "pending": 3,
  "success_rate": 0.83
}
```

---

## 二、global-macro-fin (宏观经济数据服务)

**服务地址**: `http://localhost:8094`

**基础路径**: `/api/macro`

---

### 1. 根路径

获取服务信息。

**请求**

| 属性 | 值 |
|------|-----|
| 方法 | GET |
| 路径 | `/` |

**响应示例**

```json
{
  "service": "global-macro-fin",
  "version": "1.0.0",
  "status": "running",
  "docs": "/docs"
}
```

---

### 2. 健康检查

服务健康检查，获取最后更新时间。

**请求**

| 属性 | 值 |
|------|-----|
| 方法 | GET |
| 路径 | `/api/macro/health` |

**响应**

```json
{
  "status": "healthy",
  "service": "global-macro-fin",
  "version": "1.0.0",
  "last_update": "2026-03-05"
}
```

---

### 3. 更新全部数据

n8n 调用此接口触发数据更新（美债 + 欧债 + 日债 + 汇率）。

**请求**

| 属性 | 值 |
|------|-----|
| 方法 | POST |
| 路径 | `/api/macro/update` |

**响应**

```json
{
  "success": true,
  "message": "数据更新完成",
  "updated_at": "2026-03-05T12:00:00Z",
  "data": {
    "us_treasuries": {
      "m3": {
        "date": "2026-03-05",
        "value": 4.52
      },
      "y2": {
        "date": "2026-03-05",
        "value": 4.18
      },
      "y10": {
        "date": "2026-03-05",
        "value": 4.05
      }
    },
    "eu_treasuries": {
      "y10": {
        "date": "2026-03-05",
        "value": 2.45
      }
    },
    "jp_treasuries": {
      "y10": {
        "date": "2026-03-05",
        "value": 0.98
      }
    },
    "exchange_rates": {
      "dollar_index": {
        "date": "2026-03-05",
        "value": 104.5
      },
      "usd_cny": {
        "date": "2026-03-05",
        "value": 7.24
      },
      "usd_jpy": {
        "date": "2026-03-05",
        "value": 149.8
      },
      "usd_eur": {
        "date": "2026-03-05",
        "value": 0.92
      }
    }
  }
}
```

---

### 4. 获取美国国债历史数据

从 2000 年开始获取全部美国国债历史数据。

**请求**

| 属性 | 值 |
|------|-----|
| 方法 | POST |
| 路径 | `/api/macro/fetch/us-treasuries/history` |

**响应**

```json
{
  "success": true,
  "message": "美国国债历史数据获取完成",
  "updated_at": "2026-03-05T12:00:00Z",
  "data": {
    "us_treasuries": {
      "m3": {...},
      "y2": {...},
      "y10": {...}
    }
  }
}
```

---

### 5. 增量更新美国国债数据

增量更新最近 7 天的美国国债数据。

**请求**

| 属性 | 值 |
|------|-----|
| 方法 | POST |
| 路径 | `/api/macro/update/us-treasuries` |

**响应**

```json
{
  "success": true,
  "message": "美国国债数据增量更新完成",
  "updated_at": "2026-03-05T12:00:00Z",
  "data": {
    "us_treasuries": {
      "m3": {...},
      "y2": {...},
      "y10": {...}
    }
  }
}
```

---

### 6. 获取汇率历史数据

从 2000 年开始获取全部汇率历史数据。

**请求**

| 属性 | 值 |
|------|-----|
| 方法 | POST |
| 路径 | `/api/macro/fetch/exchange-rates/history` |

**响应**

```json
{
  "success": true,
  "message": "汇率历史数据获取完成",
  "updated_at": "2026-03-05T12:00:00Z",
  "data": {
    "exchange_rates": {
      "dollar_index": {...},
      "usd_cny": {...},
      "usd_jpy": {...},
      "usd_eur": {...}
    }
  }
}
```

---

### 7. 增量更新汇率数据

增量更新最近 7 天的汇率数据。

**请求**

| 属性 | 值 |
|------|-----|
| 方法 | POST |
| 路径 | `/api/macro/update/exchange-rates` |

**响应**

```json
{
  "success": true,
  "message": "汇率数据增量更新完成",
  "updated_at": "2026-03-05T12:00:00Z",
  "data": {
    "exchange_rates": {
      "dollar_index": {...},
      "usd_cny": {...},
      "usd_jpy": {...},
      "usd_eur": {...}
    }
  }
}
```

---

### 8. 获取欧洲国债历史数据

从 2000 年开始获取全部欧洲（德国）国债历史数据。

**请求**

| 属性 | 值 |
|------|-----|
| 方法 | POST |
| 路径 | `/api/macro/fetch/eu-bonds/history` |

**响应**

```json
{
  "success": true,
  "message": "欧洲国债历史数据获取完成",
  "updated_at": "2026-03-05T12:00:00Z",
  "data": {
    "eu_treasuries": {
      "y10": {...}
    }
  }
}
```

---

### 9. 增量更新欧洲国债数据

增量更新最近 365 天的欧洲国债数据。

**请求**

| 属性 | 值 |
|------|-----|
| 方法 | POST |
| 路径 | `/api/macro/update/eu-bonds` |

**响应**

```json
{
  "success": true,
  "message": "欧洲国债数据增量更新完成",
  "updated_at": "2026-03-05T12:00:00Z",
  "data": {
    "eu_treasuries": {
      "y10": {...}
    }
  }
}
```

---

### 10. 获取日本国债历史数据

从 2000 年开始获取全部日本国债历史数据。

**请求**

| 属性 | 值 |
|------|-----|
| 方法 | POST |
| 路径 | `/api/macro/fetch/jp-bonds/history` |

**响应**

```json
{
  "success": true,
  "message": "日本国债历史数据获取完成",
  "updated_at": "2026-03-05T12:00:00Z",
  "data": {
    "jp_treasuries": {
      "y10": {...}
    }
  }
}
```

---

### 11. 增量更新日本国债数据

增量更新最近 365 天的日本国债数据。

**请求**

| 属性 | 值 |
|------|-----|
| 方法 | POST |
| 路径 | `/api/macro/update/jp-bonds` |

**响应**

```json
{
  "success": true,
  "message": "日本国债数据增量更新完成",
  "updated_at": "2026-03-05T12:00:00Z",
  "data": {
    "jp_treasuries": {
      "y10": {...}
    }
  }
}
```

---

### 12. 查询宏观经济数据

前端调用此接口获取展示数据。

**请求**

| 属性 | 值 |
|------|-----|
| 方法 | GET |
| 路径 | `/api/macro/data` |

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| start_date | string | 否 | 开始日期，格式：YYYY-MM-DD |
| end_date | string | 否 | 结束日期，格式：YYYY-MM-DD |

**响应**

```json
{
  "success": true,
  "message": "数据查询成功",
  "data": {
    "us_treasuries": {
      "m3": [
        {"date": "2026-03-01", "value": 4.48},
        {"date": "2026-03-02", "value": 4.50}
      ],
      "y2": [
        {"date": "2026-03-01", "value": 4.15},
        {"date": "2026-03-02", "value": 4.18}
      ],
      "y10": [
        {"date": "2026-03-01", "value": 4.02},
        {"date": "2026-03-02", "value": 4.05}
      ]
    },
    "eu_treasuries": {
      "y10": [
        {"date": "2026-03-01", "value": 2.42},
        {"date": "2026-03-02", "value": 2.45}
      ]
    },
    "jp_treasuries": {
      "y10": [
        {"date": "2026-03-01", "value": 0.95},
        {"date": "2026-03-02", "value": 0.98}
      ]
    },
    "exchange_rates": {
      "dollar_index": [
        {"date": "2026-03-01", "value": 104.2},
        {"date": "2026-03-02", "value": 104.5}
      ],
      "usd_cny": [
        {"date": "2026-03-01", "value": 7.21},
        {"date": "2026-03-02", "value": 7.24}
      ],
      "usd_jpy": [
        {"date": "2026-03-01", "value": 149.5},
        {"date": "2026-03-02", "value": 149.8}
      ],
      "usd_eur": [
        {"date": "2026-03-01", "value": 0.91},
        {"date": "2026-03-02", "value": 0.92}
      ]
    }
  }
}
```

---

## 数据模型

### 国债数据 (TreasuryData)

```typescript
interface TreasuryData {
  date: string;           // YYYY-MM-DD
  value: number | null;   // 收益率值
}
```

### 美国国债 (USTreasuries)

```typescript
interface USTreasuries {
  m3: TreasuryData;   // 3个月期国债
  y2: TreasuryData;   // 2年期国债
  y10: TreasuryData;  // 10年期国债
}
```

### 欧洲国债 (EUTreasuries)

```typescript
interface EUTreasuries {
  y10: TreasuryData;  // 10年期德国国债
}
```

### 日本国债 (JPTreasuries)

```typescript
interface JPTreasuries {
  y10: TreasuryData;  // 10年期日本国债
}
```

### 汇率数据 (ExchangeRateData)

```typescript
interface ExchangeRateData {
  date: string;           // YYYY-MM-DD
  value: number | null;   // 汇率值
}
```

### 汇率 (ExchangeRates)

```typescript
interface ExchangeRates {
  dollar_index: ExchangeRateData;  // 美元指数
  usd_cny: ExchangeRateData;       // 美元兑人民币
  usd_jpy: ExchangeRateData;       // 美元兑日元
  usd_eur: ExchangeRateData;       // 美元兑欧元
}
```

### 通用响应 (UpdateResponse)

```typescript
interface UpdateResponse {
  success: boolean;
  message: string;
  data?: {
    us_treasuries?: USTreasuries;
    eu_treasuries?: EUTreasuries;
    jp_treasuries?: JPTreasuries;
    exchange_rates?: ExchangeRates;
  };
  updated_at?: string;   // ISO 8601 格式
  error_code?: string;
}
```

### 数据查询响应 (DataResponse)

```typescript
interface DataResponse {
  success: boolean;
  message: string;
  data?: {
    us_treasuries?: {
      m3: TreasuryData[];
      y2: TreasuryData[];
      y10: TreasuryData[];
    };
    eu_treasuries?: {
      y10: TreasuryData[];
    };
    jp_treasuries?: {
      y10: TreasuryData[];
    };
    exchange_rates?: {
      dollar_index: ExchangeRateData[];
      usd_cny: ExchangeRateData[];
      usd_jpy: ExchangeRateData[];
      usd_eur: ExchangeRateData[];
    };
  };
  error_code?: string;
}
```

### 健康检查响应 (HealthResponse)

```typescript
interface HealthResponse {
  status: string;
  service: string;
  version: string;
  last_update?: string;
}
```

---

## API 接口汇总表

| 服务 | 序号 | 路径 | 方法 | 功能 |
|------|------|------|------|------|
| **douyin-processor** (8093) | 1 | `/` | GET | 根路径服务信息 |
| | 2 | `/health` | GET | 健康检查 |
| | 3 | `/api/macro/process/async` | POST | 异步处理视频 |
| | 4 | `/api/macro/process` | POST | 同步处理视频 |
| | 5 | `/api/macro/videos` | GET | 获取视频列表 |
| | 6 | `/api/macro/videos/{aweme_id}` | GET | 获取视频详情 |
| | 7 | `/api/macro/videos/{aweme_id}/result` | GET | 获取视频处理结果 |
| | 8 | `/api/macro/videos/{aweme_id}/read` | POST | 标记已读/未读 |
| | 9 | `/api/macro/videos/{aweme_id}` | DELETE | 删除视频 |
| | 10 | `/api/macro/stats` | GET | 获取统计信息 |
| **global-macro-fin** (8094) | 1 | `/` | GET | 根路径服务信息 |
| | 2 | `/api/macro/health` | GET | 健康检查 |
| | 3 | `/api/macro/update` | POST | 更新全部数据 |
| | 4 | `/api/macro/fetch/us-treasuries/history` | POST | 获取美债历史数据 |
| | 5 | `/api/macro/update/us-treasuries` | POST | 增量更新美债 |
| | 6 | `/api/macro/fetch/exchange-rates/history` | POST | 获取汇率历史数据 |
| | 7 | `/api/macro/update/exchange-rates` | POST | 增量更新汇率 |
| | 8 | `/api/macro/fetch/eu-bonds/history` | POST | 获取欧债历史数据 |
| | 9 | `/api/macro/update/eu-bonds` | POST | 增量更新欧债 |
| | 10 | `/api/macro/fetch/jp-bonds/history` | POST | 获取日债历史数据 |
| | 11 | `/api/macro/update/jp-bonds` | POST | 增量更新日债 |
| | 12 | `/api/macro/data` | GET | 查询宏观经济数据 |