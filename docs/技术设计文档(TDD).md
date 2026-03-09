# 技术设计文档 (TDD)

## 项目概述

**项目名称**: Global Macro Finance API (全球宏观经济债券利率数据服务)

**版本**: v1.0.0

**最后更新**: 2026-03-03

---

## 1. 系统架构

### 1.1 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                         前端应用                            │
│                  (React / Vue / 其他)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ HTTP/REST
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI 服务                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                   路由层 (routes)                    │  │
│  │  • /api/fetch/us-treasuries/history                  │  │
│  │  • /api/update/us-treasuries                         │  │
│  │  • /api/update                                       │  │
│  │  • /api/data                                         │  │
│  │  • /api/health                                       │  │
│  └───────────────────┬──────────────────────────────────┘  │
│                      │                                       │
│  ┌───────────────────▼──────────────────────────────────┐  │
│  │                 服务层 (services)                    │  │
│  │  • FredService - FRED API 数据获取                   │  │
│  │  • DataService - 数据存储管理                        │  │
│  └───────────────────┬──────────────────────────────────┘  │
│                      │                                       │
│  ┌───────────────────▼──────────────────────────────────┐  │
│  │                 数据层 (data)                         │  │
│  │  • CSV 文件存储                                       │  │
│  │  • us_treasuries.csv                                  │  │
│  │  • eu_bonds.csv                                       │  │
│  │  • jp_bonds.csv                                       │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            │ HTTPS
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     FRED API                                │
│          (Federal Reserve Economic Data)                   │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 技术栈

| 层级 | 技术选择 | 版本 | 说明 |
|------|----------|------|------|
| Web 框架 | FastAPI | 0.135+ | 高性能异步框架 |
| ASGI 服务器 | Uvicorn | 0.32+ | 异步服务器 |
| 数据处理 | Pandas | 2.0+ | 数据处理和分析 |
| HTTP 客户端 | fredapi | 0.5+ | FRED API 客户端 |
| 配置管理 | Pydantic Settings | 2.0+ | 类型安全配置 |
| 数据存储 | CSV | - | 文件存储 |

---

## 2. 模块设计

### 2.1 目录结构

```
global-macro-fin/
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   ├── config.py               # 配置管理
│   ├── models.py               # 数据模型定义
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py           # API 路由定义
│   ├── services/
│   │   ├── __init__.py
│   │   ├── fred_service.py     # FRED API 服务
│   │   └── data_service.py     # 数据存储服务
│   └── utils/
│       ├── __init__.py
│       ├── logger.py           # 日志工具
│       └── retry.py            # 重试装饰器
├── data/                       # 数据存储目录
│   ├── us_treasuries.csv
│   ├── eu_bonds.csv
│   └── jp_bonds.csv
├── logs/                      # 日志目录
│   └── service.log
├── docs/                      # 文档目录
├── tests/                     # 测试目录
├── .env                       # 环境配置
├── pyproject.toml             # 项目配置
└── requirements.txt           # 依赖列表
```

### 2.2 核心模块

#### 2.2.1 FredService

**职责**: 从 FRED API 获取经济数据

**核心方法**:
```python
async def fetch_series(code: str, start_date: Timestamp, end_date: Timestamp) -> Series
```

**关键特性**:
- 自动检测 OECD 月度数据并扩展查询范围到 365 天
- 支持重试机制（最多 3 次）
- 异步并发获取多个数据系列

#### 2.2.2 DataService

**职责**: 管理本地数据存储

**核心方法**:
```python
def save_fred_data(data: Dict[str, Series]) -> None
def query_data(start_date: Optional[str], end_date: Optional[str]) -> Dict
def get_last_date(data_type: str) -> Optional[Timestamp]
```

**关键特性**:
- CSV 文件增量追加
- 自动去重（保留最新数据）
- 缺失值前向填充

#### 2.2.3 Routes

**职责**: 定义 API 接口

**核心接口**:
- `fetch_us_treasuries_history()`: 获取历史数据
- `update_us_treasuries()`: 增量更新
- `update_data()`: 完整更新
- `get_data()`: 数据查询
- `health_check()`: 健康检查

**关键特性**:
- 全局更新锁（并发控制）
- 统一错误处理
- 类型安全的响应模型

n#### 2.2.4 VIXService

**职责**: 处理VIX恐慌指数数据

**核心方法**:
```python
def convert_timezone(data: pd.Series) -> pd.Series
    """转换时区（ET → UTC）"""

def validate_data(data: pd.Series) -> pd.Series
    """验证和清洗VIX数据"""

def normalize_data(data: pd.Series) -> pd.Series
    """标准化VIX数据格式"""
```

**关键特性**:
- VIX数据时区转换（ET → UTC）
- 异常值检测（VIX > 100 或 < 0）
- 前向填充非交易日数据
---

## 3. 数据模型设计

### 3.1 API 响应模型

```python
# 美债更新响应数据
class USTreasuriesUpdateData(BaseModel):
    us_treasuries: USTreasuries

# 完整宏观经济数据
class MacroData(BaseModel):
    us_treasuries: USTreasuries
    eu_10y: TreasuryData
    jp_10y: TreasuryData

# 更新响应（支持两种类型）
class UpdateResponse(BaseModel):
    success: bool
    message: str
    data: Optional[USTreasuriesUpdateData | MacroData] = None
    updated_at: Optional[str] = None
    error_code: Optional[str] = None
```

### 3.2 本地数据存储

#### CSV 文件结构

**us_treasuries.csv**:
```csv
,美债3m,美债2y,美债10y
2000-01-03,5.48,6.38,6.58
2000-01-04,5.43,6.30,6.49
```

**eu_bonds.csv**:
```csv
,德债10y
2000-01-01,2.50
2000-02-01,2.45
```

**jp_bonds.csv**:
```csv
,日债10y
2000-01-01,1.75
2000-02-01,1.80
```

---

## 4. 接口设计

### 4.1 获取历史数据

**接口**: `POST /api/fetch/us-treasuries/history`

**实现逻辑**:
1. 检查是否正在更新（全局锁）
2. 设置起始日期为 2000-01-01
3. 调用 FRED API 获取美债数据
4. 保存到 CSV 文件
5. 返回最新数据点

**代码位置**: `src/api/routes.py:131-194`

### 4.2 增量更新

**接口**: `POST /api/update/us-treasuries`

**实现逻辑**:
1. 检查是否正在更新（全局锁）
2. 设置起始日期为当前日期 - 7 天
3. 调用 FRED API 获取美债数据
4. 追加到 CSV 文件
5. 返回最新数据点

**代码位置**: `src/api/routes.py:197-260`

### 4.3 数据查询

**接口**: `GET /api/data`

**实现逻辑**:
1. 解析查询参数（默认最近 90 天）
2. 加载 CSV 文件
3. 前向填充缺失值
4. 按日期范围筛选
5. 返回格式化数据

**代码位置**: `src/api/routes.py:300-320`

---

## 5. 技术实现更新

### 2026-03-03 - v1.0.0

#### 新增功能
- **新增历史数据获取接口**
  - 代码位置: `src/api/routes.py:131-194`
  - 技术方案: 直接从 FRED API 获取 2000-01-01 至今的全部数据
  - 响应时间: 约 30-40 秒

- **新增增量更新接口**
  - 代码位置: `src/api/routes.py:197-260`
  - 技术方案: 获取最近 7 天数据并追加到本地存储
  - 响应时间: 约 3-5 秒

#### 优化改进
- **OECD 数据自动扩展**
  - 代码位置: `src/services/fred_service.py:36-40`
  - 技术方案: 检测 OECD 代码，自动使用 365 天查询范围
  - 依赖关系: FredService.fetch_series()

- **并发控制机制**
  - 代码位置: `src/api/routes.py:24-38`
  - 技术方案: 全局更新锁，防止并发更新冲突

- **响应模型优化**
  - 代码位置: `src/models.py:22-25`
  - 技术方案: 新增 USTreasuriesUpdateData 模型
  - 支持联合类型: `USTreasuriesUpdateData | MacroData`

n### 2026-03-08 - v1.1.0

#### 新增功能
- **新增VIX恐慌指数数据模块**
  - 代码位置: `src/services/vix_service.py`
  - 技术方案: 独立的VIX服务模块，负责时区转换、数据验证和格式标准化

- **新增VIX历史数据获取接口**
  - 代码位置: `src/api/routes.py:fetch_vix_history()`
  - 接口路径: `POST /api/macro/fetch/vix/history`
  - 技术方案: 从FRED API获取VIXCLS序列，从2000年开始获取全部历史数据

- **新增VIX增量更新接口**
  - 代码位置: `src/api/routes.py:update_vix()`
  - 接口路径: `POST /api/macro/update/vix`
  - 技术方案: 获取最近7天VIX数据并追加到本地存储

#### 优化改进
- **数据查询接口扩展**
  - 代码位置: `src/services/data_service.py:query_data()`
  - 技术方案: 返回数据中包含VIX指数数组

- **健康检查接口扩展**
  - 代码位置: `src/api/routes.py:health_check()`
  - 技术方案: 健康检查返回VIX数据的最后更新时间

- **新增数据模型**
  - 代码位置: `src/models.py`
  - 技术方案: 新增VIXData和VIXUpdateData模型
---

## 6. 数据流设计

### 6.1 数据获取流程

```
┌─────────────┐
│  n8n/前端   │
└──────┬──────┘
       │ HTTP POST
       ↓
┌─────────────────────────────────┐
│     FastAPI 路由层              │
│  • 并发控制检查                  │
│  • 确定查询范围                  │
└──────┬──────────────────────────┘
       │
       ↓
┌─────────────────────────────────┐
│     FredService                 │
│  • 构建查询参数                  │
│  • 调用 fredapi                 │
│  • 重试机制（3次）               │
└──────┬──────────────────────────┘
       │
       ↓ HTTPS
┌─────────────────────────────────┐
│     FRED API                    │
│  • 验证 API Key                 │
│  • 返回时间序列数据              │
└──────┬──────────────────────────┘
       │
       ↓
┌─────────────────────────────────┐
│     DataService                │
│  • 解析数据                     │
│  • 追加到 CSV                   │
│  • 去重合并                     │
└──────┬──────────────────────────┘
       │
       ↓
┌─────────────────────────────────┐
│     CSV 文件存储                │
│  • us_treasuries.csv            │
│  • eu_bonds.csv                 │
│  • jp_bonds.csv                 │
└─────────────────────────────────┘
```

### 6.2 数据查询流程

```
┌─────────────┐
│   前端应用   │
└──────┬──────┘
       │ HTTP GET
       │
       ↓
┌─────────────────────────────────┐
│     FastAPI 路由层              │
│  • 解析查询参数                  │
│  • 设置默认范围（90天）           │
└──────┬──────────────────────────┘
       │
       ↓
┌─────────────────────────────────┐
│     DataService                │
│  • 加载 CSV 文件                │
│  • 前向填充缺失值                │
│  • 时间范围筛选                  │
│  • 格式转换                     │
└──────┬──────────────────────────┘
       │
       ↓ JSON
┌─────────────┐
│   前端应用   │
└─────────────┘
```

---

## 7. 安全设计

### 7.1 API Key 管理
- 使用环境变量存储 FRED API Key
- .env 文件不提交到版本控制
- 提供 .env.example 模板

### 7.2 CORS 配置
- 允许所有来源（开发环境）
- 生产环境需要限制来源

### 7.3 并发控制
- 全局更新锁
- 防止重复更新
- 优雅的错误提示

---

## 8. 监控与日志

### 8.1 日志策略
- 日志位置: `./logs/service.log`
- 日志级别: INFO
- 关键操作记录:
  - 数据更新开始/完成
  - API 调用成功/失败
  - 数据保存操作

### 8.2 健康检查
- 接口: `GET /api/health`
- 返回信息:
  - 服务状态
  - 最后更新时间
  - 版本号

---

## 9. 部署架构

### 9.1 本地开发

```bash
# 启动服务
uvicorn src.main:app --host 0.0.0.0 --port 8094 --reload

# 访问文档
http://localhost:8094/docs
```

### 9.2 Docker 部署

```dockerfile
FROM python:3.14-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8094"]
```

### 9.3 n8n 集成

```json
{
  "nodes": [
    {
      "name": "Cron",
      "type": "n8n-nodes-base.cron",
      "parameters": {
        "cronExpression": "0 2 * * *"
      }
    },
    {
      "name": "HTTP Request",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://global-macro-fin:8094/api/update/us-treasuries",
        "method": "POST"
      }
    }
  ]
}
```

---

## 10. 依赖关系

### 10.1 外部依赖
- FRED API: 数据源
- fredapi 库: FRED API 客户端

### 10.2 内部依赖
```
routes.py → fred_service.py
routes.py → data_service.py
routes.py → models.py
fred_service.py → config.py
data_service.py → config.py
```
