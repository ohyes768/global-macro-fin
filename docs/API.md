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

### 数据范围说明

| 数据类型 | 期种 | 数据频率 | 说明 |
|---------|------|---------|------|
| 美国国债 | 3 个月、2 年、10 年 | 日级 | 美国国债收益率曲线 |
| 欧洲国债 | 3 个月、2 年、10 年 | 日级 | 德国国债收益率曲线 |
| 日本国债 | 10 年 | 日级 | 日本 10 年期国债收益率（注） |
| 汇率数据 | 美元指数、USD/CNY、USD/JPY、USD/EUR | 日级 | 主要货币汇率 |
| VIX恐慌指数 | VIXCLS | 日级 | CBOE波动率指数 |
| 资金流向 | 北向资金、南向资金 | 日级 | 沪深港通资金流向 |

> **注**: 日本国债目前仅实现 10 年期数据。响应数据结构中保留 `3m` 和 `2y` 字段但返回空数组，待后续补充数据源。

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
    },
    "fund_flow": {
      "north_net_flow": [45.2, 52.3],
      "north_buy": [145.5, 158.5],
      "north_sell": [100.3, 106.2],
      "south_net_flow": [15.5, 18.7],
      "south_buy": [80.2, 85.3],
      "south_sell": [64.7, 66.6]
    }
  }
}
```

n---

### 13. 获取VIX历史数据

从 2000 年开始获取全部 VIX 恐慌指数历史数据。

**请求**

| 属性 | 值 |
|------|-----|
| 方法 | POST |
| 路径 | `/api/macro/fetch/vix/history` |

**响应**

```json
{
  "success": true,
  "message": "VIX历史数据获取成功",
  "updated_at": "2026-03-08T12:00:00Z",
  "data": {
    "vix": {
      "date": "2026-03-08",
      "value": 18.52
    }
  }
}
```

---

### 14. 增量更新VIX数据

增量更新最近 7 天的 VIX 恐慌指数数据。

**请求**

| 属性 | 值 |
|------|-----|
| 方法 | POST |
| 路径 | `/api/macro/update/vix` |

**响应**

```json
{
  "success": true,
  "message": "VIX数据增量更新成功",
  "updated_at": "2026-03-08T12:00:00Z",
  "data": {
    "vix": {
      "date": "2026-03-08",
      "value": 18.52
    }
  }
}
```

---

### 15. 获取资金流向历史数据

从 2014-11-17（沪港通开通日）开始获取全部资金流向历史数据。

**请求**

| 属性 | 值 |
|------|-----|
| 方法 | POST |
| 路径 | `/api/macro/fetch/fund-flow/history` |

**响应**

```json
{
  "success": true,
  "message": "资金流向历史数据获取成功",
  "updated_at": "2026-03-12T12:00:00Z",
  "data": {
    "fund_flow": {
      "north": {
        "date": "2026-03-12",
        "net_flow": 52.3,
        "buy": 158.5,
        "sell": 106.2
      },
      "south": {
        "date": "2026-03-12",
        "net_flow": 18.7,
        "buy": 85.3,
        "sell": 66.6
      }
    }
  }
}
```

---

### 16. 增量更新资金流向数据

增量更新最近 7 天的资金流向数据。

**请求**

| 属性 | 值 |
|------|-----|
| 方法 | POST |
| 路径 | `/api/macro/update/fund-flow` |

**响应**

```json
{
  "success": true,
  "message": "资金流向数据增量更新成功",
  "updated_at": "2026-03-12T12:00:00Z",
  "data": {
    "fund_flow": {
      "north": {
        "date": "2026-03-12",
        "net_flow": 52.3,
        "buy": 158.5,
        "sell": 106.2
      },
      "south": {
        "date": "2026-03-12",
        "net_flow": 18.7,
        "buy": 85.3,
        "sell": 66.6
      }
    }
  }
}
```

---

### 17. 获取资金流向累计数据

获取北向/南向资金的 7 日和 30 日累计净流入。

**请求**

| 属性 | 值 |
|------|-----|
| 方法 | GET |
| 路径 | `/api/macro/fund-flow/cumulative` |

**响应**

```json
{
  "north_cumulative": {
    "date": "2026-03-12",
    "cum_7d": 325.5,
    "cum_30d": 1250.8
  },
  "south_cumulative": {
    "date": "2026-03-12",
    "cum_7d": 112.3,
    "cum_30d": 450.6
  }
}
```

**字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| north_cumulative | object | 北向资金累计数据 |
| south_cumulative | object | 南向资金累计数据 |
| date | string | 计算截止日期（YYYY-MM-DD） |
| cum_7d | number | 7 日累计净流入（亿元） |
| cum_30d | number | 30 日累计净流入（亿元） |

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
    vix?: VIXData;
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
    vix?: number[];
  };
  error_code?: string;
}
```

n### VIX恐慌指数数据 (VIXData)

```typescript
interface VIXData {
  date: string;           // YYYY-MM-DD
  value: number | null;   // VIX指数值
}
```

### VIX更新响应数据 (VIXUpdateData)

```typescript
interface VIXUpdateData {
  vix: VIXData;
}
```

### 资金流向数据 (FundFlowData)

```typescript
interface FundFlowData {
  date: string;           // YYYY-MM-DD
  net_flow: number;       // 净流入（亿元）
  buy: number;            // 买入额（亿元）
  sell: number;           // 卖出额（亿元）
}
```

### 资金流向 (FundFlow)

```typescript
interface FundFlow {
  north: FundFlowData;    // 北向资金
  south: FundFlowData;    // 南向资金
}
```

### 资金流向更新响应数据 (FundFlowUpdateData)

```typescript
interface FundFlowUpdateData {
  fund_flow: FundFlow;
}
```

### 资金流向累计数据 (FundFlowCumulativeData)

```typescript
interface FundFlowCumulativeData {
  date: string;           // YYYY-MM-DD
  cum_7d: number | null;  // 7 日累计净流入（亿元）
  cum_30d: number | null; // 30 日累计净流入（亿元）
}
```

### 资金流向累计响应 (FundFlowCumulativeResponse)

```typescript
interface FundFlowCumulativeResponse {
  north_cumulative: FundFlowCumulativeData;
  south_cumulative: FundFlowCumulativeData;
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
| | 13 | `/api/macro/fetch/vix/history` | POST | 获取VIX历史数据 |
| | 14 | `/api/macro/update/vix` | POST | 增量更新VIX |
| | 15 | `/api/macro/fetch/fund-flow/history` | POST | 获取资金流向历史数据 |
| | 16 | `/api/macro/update/fund-flow` | POST | 增量更新资金流向 |
| | 17 | `/api/macro/fund-flow/cumulative` | GET | 获取资金流向累计数据 |
