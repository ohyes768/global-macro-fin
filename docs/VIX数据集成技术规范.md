# VIX恐慌指数数据集成技术规范

## 1. 概述

### 1.1 目标
在汇率/美债Tab页上增加第三个子图，显示CBOE VIX恐慌指数曲线，用于分析市场情绪波动。

### 1.2 架构决策
**数据源方案：纯FRED方案**
- 使用FRED API的VIXCLS序列获取历史和实时数据
- 不集成阿里云API，简化架构和维护
- 复用现有FRED服务基础设施

### 1.3 调研结论
- **FRED VIXCLS序列**：可提供从1990年1月1日开始的完整VIX历史数据
- **数据类型**：每日数据，包含收盘价
- **更新频率**：每日（非交易日无数据）
- **数据单位**：指数点数（通常在10-80之间波动）
- **API限制**：FRED API与现有美债/汇率使用同一API密钥，无额外限制

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                          前端层                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Tab:       │  │   Tab:       │  │   Tab:       │          │
│  │ 汇率/美债    │  │   德债日债   │  │   (其他)     │          │
│  │              │  │              │  │              │          │
│  │ ┌────────┐   │  │ ┌────────┐   │  │ ┌────────┐   │          │
│  │ │美债图  │   │  │ │德债图  │   │  │ │        │   │          │
│  │ └────────┘   │  │ └────────┘   │  │ └────────┘   │          │
│  │ ┌────────┐   │  │ └────────┘   │  │              │          │
│  │ │汇率图  │   │  │              │  │              │          │
│  │ └────────┘   │  │              │  │              │          │
│  │ ┌────────┐   │  │              │  │              │          │
│  │ │VIX图   │   │  │              │  │              │          │
│  │ └────────┘   │  │              │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        API层 (FastAPI)                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ GET  /api/macro/data                                     │  │
│  │      (返回美债+汇率+VIX数据)                             │  │
│  │                                                          │  │
│  │ POST /api/macro/fetch/vix/history                        │  │
│  │      (获取VIX历史数据，从2000年开始)                     │  │
│  │                                                          │  │
│  │ POST /api/macro/update/vix                               │  │
│  │      (增量更新VIX数据，最近7天)                          │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      服务层 (Services)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ FredService  │  │ DataService  │  │ VIXService   │          │
│  │ (现有)       │  │ (扩展)       │  │ (新建)       │          │
│  │              │  │              │  │              │          │
│  │ - 调用FRED   │  │ - CSV存储    │  │ - VIX数据    │          │
│  │ API         │  │ - 数据查询    │  │   获取       │          │
│  │              │  │ - 日期对齐   │  │ - 时区转换   │          │
│  │              │  │              │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    数据层 (Data Storage)                        │
│  ./data/vix.csv                                                │
│  ┌──────────────┬────────────────┐                            │
│  │    Date      │  Close_VIX     │                            │
│  ├──────────────┼────────────────┤                            │
│  │  2000-01-01  │     25.32      │                            │
│  │  2000-01-02  │     24.15      │                            │
│  │     ...      │      ...       │                            │
│  └──────────────┴────────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    外部API (FRED API)                           │
│  Series Code: VIXCLS                                            │
│  Description: CBOE Volatility Index: VIX                        │
│  Frequency: Daily                                               │
│  Source: Federal Reserve Bank of St. Louis                     │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 技术栈

| 层次 | 技术选型 | 说明 |
|------|---------|------|
| 前端 | React + Plotly.js | 动态图表渲染 |
| 后端 | FastAPI + Python | RESTful API |
| 数据库 | CSV文件 | 本地持久化存储 |
| 数据源 | FRED API | VIXCLS序列 |
| 并发控制 | 全局锁机制 | 复用现有_update_lock |

---

## 3. API设计

### 3.1 获取VIX历史数据

**接口地址**
```
POST /api/macro/fetch/vix/history
```

**请求参数**
无

**响应示例**
```json
{
  "success": true,
  "message": "VIX历史数据获取成功",
  "data": {
    "vix": {
      "date": "2026-03-08",
      "value": 18.52
    }
  },
  "updated_at": "2026-03-08T10:30:00"
}
```

**错误响应**
```json
{
  "success": false,
  "message": "VIX数据获取失败: API调用超时",
  "error_code": "UPDATE_FAILED"
}
```

### 3.2 增量更新VIX数据

**接口地址**
```
POST /api/macro/update/vix
```

**请求参数**
无

**响应示例**
```json
{
  "success": true,
  "message": "VIX数据增量更新成功",
  "data": {
    "vix": {
      "date": "2026-03-08",
      "value": 18.52
    }
  },
  "updated_at": "2026-03-08T10:30:00"
}
```

### 3.3 查询数据（扩展）

**接口地址**
```
GET /api/macro/data
```

**请求参数**（不变）
- `start_date`: 起始日期 (YYYY-MM-DD)
- `end_date`: 结束日期 (YYYY-MM-DD)

**响应示例**（扩展）
```json
{
  "success": true,
  "message": "数据查询成功",
  "data": {
    "dates": ["2026-01-01", "2026-01-02", ...],
    "us_treasuries": {
      "3m": [1.25, 1.27, ...],
      "2y": [2.35, 2.37, ...],
      "10y": [3.85, 3.87, ...]
    },
    "eu_treasuries": {
      "3m": [2.15, 2.16, ...],
      "2y": [2.45, 2.46, ...],
      "10y": [2.78, 2.79, ...]
    },
    "jp_treasuries": {
      "3m": [],
      "2y": [],
      "10y": [0.95, 0.96, ...]
    },
    "exchange_rates": {
      "dollar_index": [102.5, 102.7, ...],
      "usd_cny": [7.25, 7.26, ...],
      "usd_jpy": [149.2, 149.3, ...],
      "usd_eur": [0.92, 0.92, ...]
    },
    "vix": [18.5, 19.2, 17.8, ...]
  }
}
```

---

## 4. 数据模型

### 4.1 后端数据模型

**VIXData** (src/models.py)
```python
class VIXData(BaseModel):
    """VIX恐慌指数数据"""

    date: date
    value: Optional[float] = None
```

**VIXUpdateData** (src/models.py)
```python
class VIXUpdateData(BaseModel):
    """VIX更新响应数据"""

    vix: VIXData
```

### 4.2 CSV文件结构

**文件路径**: `./data/vix.csv`

**文件结构**:
```csv
Date,Close_VIX
2000-01-03,22.47
2000-01-04,23.65
2000-01-05,24.12
...
```

**字段说明**:
| 字段名 | 类型 | 说明 |
|--------|------|------|
| Date | Date | 日期（YYYY-MM-DD格式） |
| Close_VIX | Float | VIX指数收盘价 |

### 4.3 配置扩展

**src/config.py** - 扩展FRED代码配置:
```python
fred_codes: dict = {
    # ... 现有代码 ...
    # VIX恐慌指数
    "vix": "VIXCLS",
}
```

---

## 5. 服务层实现

### 5.1 VIX服务

**文件路径**: `src/services/vix_service.py`

**主要功能**:
- 从FRED API获取VIX数据
- 时区转换（ET → UTC）
- 数据验证和清洗

**核心方法**:
```python
class VIXService:
    async def fetch_vix_data(
        self,
        start_date: pd.Timestamp,
        end_date: pd.Timestamp
    ) -> pd.Series:
        """获取VIX数据"""

    def convert_timezone(self, data: pd.Series) -> pd.Series:
        """转换时区（ET → UTC）"""
```

### 5.2 数据服务扩展

**文件路径**: `src/services/data_service.py`

**扩展内容**:
- 添加VIX文件路径映射
- 添加`_save_vix`方法
- 扩展`query_data`方法，返回VIX数据

**核心方法**:
```python
def _save_vix(self, data: Dict[str, pd.Series]) -> None:
    """保存VIX数据"""

def query_data(
    self,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict:
    """查询数据（扩展包含VIX）"""
```

---

## 6. 前端实现

### 6.1 组件结构

```
EconomicChart.tsx (扩展)
├── US Treasury Chart (子图1)
├── Exchange Rate Chart (子图2)
└── VIX Chart (子图3) ← 新增
```

### 6.2 VIX图表配置

**图表类型**: 折线图 (Line Chart)

**数据展示**:
- 仅显示VIX收盘价（Close_VIX）

**布局**:
- 独立子图（第3行）
- 独立的X轴和Y轴
- 不与其他子图共用Y轴

**样式配置**:
```typescript
{
  type: 'scatter',
  mode: 'lines',
  line: {
    color: '#9467BD',  // 紫色
    width: 2
  },
  name: 'VIX恐慌指数'
}
```

### 6.3 数据加载时机

**触发条件**: 用户切换到"汇率/美债"Tab时

**加载策略**:
1. 自动调用`/api/macro/data`接口
2. 接口返回数据中包含`vix`数组
3. 前端解析VIX数据并渲染到第三个子图

**错误处理**:
- 如果VIX数据为空或获取失败，显示空图表
- 不影响其他子图的正常展示（优雅降级）

### 6.4 数据对齐

**策略**: 保留所有日期

**实现**:
- VIX数据保留所有日期（包括非交易日）
- 非交易日数据使用前向填充（forward fill）
- 与美债/汇率的日期序列保持一致

---

## 7. 并发控制

### 7.1 锁机制

**复用现有锁**: `_update_lock` 和 `_is_updating`

**锁的使用场景**:
- VIX历史数据获取 (`/api/macro/fetch/vix/history`)
- VIX增量更新 (`/api/macro/update/vix`)
- 综合数据更新 (`/api/macro/update`)

### 7.2 并发控制流程

```
1. 请求到达
   ↓
2. 检查 _is_updating
   ↓
3. 如果正在更新，返回错误
   ↓
4. 调用 acquire_update_lock()
   ↓
5. 执行数据更新
   ↓
6. 调用 release_update_lock()
   ↓
7. 返回响应
```

---

## 8. 数据更新策略

### 8.1 历史数据获取

**接口**: `POST /api/macro/fetch/vix/history`

**时间范围**: 从2000年1月1日至今

**调用场景**:
- 首次部署
- 数据文件损坏或丢失

### 8.2 增量数据更新

**接口**: `POST /api/macro/update/vix`

**时间范围**: 最近7天

**调用场景**:
- 定时任务（每日更新）
- 手动触发更新

### 8.3 综合更新

**接口**: `POST /api/macro/update` (扩展)

**更新内容**:
- 美债数据（最近7天）
- 汇率数据（最近7天）
- **VIX数据（最近7天）** ← 新增

---

## 9. 时区处理

### 9.1 VIX数据时区

**数据源时区**: 美国东部时区 (ET)

**转换策略**: ET → UTC

**实现方式**:
```python
def convert_timezone(self, data: pd.Series) -> pd.Series:
    """转换时区（ET → UTC）"""
    data.index = data.index.tz_localize('US/Eastern').tz_convert('UTC')
    return data
```

### 9.2 存储时区

**CSV存储**: 使用UTC时区

**查询返回**: 日期格式为`YYYY-MM-DD`（无时区信息）

---

## 10. 错误处理

### 10.1 API错误处理

| 错误类型 | 错误代码 | 处理方式 |
|---------|---------|---------|
| 正在更新 | UPDATE_IN_PROGRESS | 返回友好提示 |
| API调用失败 | API_ERROR | 记录日志，返回错误 |
| 数据解析失败 | PARSE_ERROR | 记录日志，返回错误 |
| 文件操作失败 | FILE_ERROR | 记录日志，返回错误 |

### 10.2 前端错误处理

**策略**: 优雅降级

**实现**:
```typescript
if (!vixData || vixData.length === 0) {
  // 显示空图表
  return <EmptyChart message="VIX数据暂不可用" />
}
```

---

## 11. 性能优化

### 11.1 数据缓存

**缓存策略**: localStorage缓存1小时

**实现**:
```typescript
const cacheKey = `vix_data_${start_date}_${end_date}`;
const cachedData = localStorage.getItem(cacheKey);
if (cachedData && !isExpired(cachedData)) {
  return JSON.parse(cachedData);
}
```

### 11.2 数据分页

**查询优化**:
- 默认查询最近90天数据
- 支持按时间范围查询
- 避免一次性加载全部历史数据

---

## 12. 测试计划

### 12.1 单元测试

| 模块 | 测试内容 |
|------|---------|
| VIXService | 数据获取、时区转换、数据验证 |
| DataService | VIX数据保存、查询、去重 |
| API Routes | 接口响应、错误处理、并发控制 |

### 12.2 集成测试

| 场景 | 测试内容 |
|------|---------|
| 历史数据获取 | 从2000年开始获取完整VIX数据 |
| 增量更新 | 验证最近7天数据的更新 |
| 日期对齐 | 验证VIX数据与美债/汇率数据的日期对齐 |
| 并发控制 | 验证并发请求的处理 |

### 12.3 前端测试

| 场景 | 测试内容 |
|------|---------|
| 图表渲染 | VIX图表正常显示 |
| 数据加载 | Tab切换时自动加载VIX数据 |
| 错误处理 | VIX数据为空时显示空图表 |
| 性能 | 大数据量下的渲染性能 |

---

## 13. 部署清单

### 13.1 后端部署

| 项目 | 说明 |
|------|------|
| 新增文件 | `src/services/vix_service.py` |
| 修改文件 | `src/config.py` |
| 修改文件 | `src/models.py` |
| 修改文件 | `src/services/data_service.py` |
| 修改文件 | `src/api/routes.py` |

### 13.2 前端部署

| 项目 | 说明 |
|------|------|
| 修改文件 | `src/app/modules/economic/components/EconomicChart.tsx` |
| 修改文件 | `src/lib/hooks/useEconomicData.ts` |
| 修改文件 | `src/lib/types/economic.ts` |

### 13.3 数据初始化

1. 调用 `POST /api/macro/fetch/vix/history` 获取历史数据
2. 验证 `./data/vix.csv` 文件已创建
3. 检查数据完整性

---

## 14. 监控与日志

### 14.1 日志记录

| 场景 | 日志级别 | 日志内容 |
|------|---------|---------|
| 数据获取 | INFO | 开始获取VIX数据 |
| 数据获取成功 | INFO | 成功获取N条VIX记录 |
| 数据获取失败 | ERROR | VIX数据获取失败: {error} |
| 数据保存 | INFO | 已保存VIX数据到文件 |
| 并发冲突 | WARN | 数据更新正在进行中 |

### 14.2 健康检查

**接口**: `GET /api/macro/health`

**响应扩展**:
```json
{
  "status": "healthy",
  "service": "global-macro-fin",
  "version": "1.0.0",
  "last_update": {
    "us_treasuries": "2026-03-08",
    "eu_bonds": "2026-03-01",
    "jp_bonds": "2026-03-01",
    "exchange_rates": "2026-03-08",
    "vix": "2026-03-08"  // 新增
  }
}
```

---

## 15. 附录

### 15.1 FRED API参考

**VIXCLS序列详情**:
- **Series ID**: VIXCLS
- **Title**: CBOE Volatility Index: VIX
- **Source**: Chicago Board Options Exchange (CBOE)
- **Release**: CBOE Daily Market Statistics
- **Seasonal Adjustment**: Not Seasonally Adjusted
- **Frequency**: Daily
- **Units**: Index
- **Date Range**: 1990-01-01 to Present

**API调用示例**:
```python
from fredapi import Fred

fred = Fred(api_key=settings.fred_api_key)
vix_data = fred.get_series(
    'VIXCLS',
    observation_start='2000-01-01',
    observation_end='2026-03-08'
)
```

### 15.2 颜色方案

| 数据项 | 颜色代码 | 说明 |
|--------|---------|------|
| 美债3m | #1F77B4 | 蓝色 |
| 美债2y | #2CA02C | 绿色 |
| 美债10y | #FF7F0E | 橙色 |
| 美元指数 | #17BECF | 青色 |
| 美元人民币 | #E377C2 | 粉色 |
| 美元日元 | #FF7F0E | 橙色 |
| 美元欧元 | #2CA02C | 绿色 |
| **VIX** | **#9467BD** | **紫色** |

### 15.3 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0.0 | 2026-03-08 | 初始版本 |

---

## 16. 参考资料

1. [FRED API Documentation](https://fred.stlouisfed.org/docs/api/fred/)
2. [CBOE VIX Index](https://www.cboe.com/tradable_products/vix/)
3. [Plotly.js Documentation](https://plotly.com/javascript/)
4. 项目现有文档

---

**文档版本**: 1.0.0
**编写日期**: 2026-03-08
**维护人员**: 开发团队