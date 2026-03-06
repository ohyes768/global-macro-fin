# 宏观数据获取逻辑文档

## 数据源概览

| 数据源 | API 端点 | 用途 | 数据频率 |
|--------|----------|------|----------|
| **FRED API** | `https://api.stlouisfed.org/fred/series/observations` | 美债、欧债(部分)、日债、汇率 | 日度/月度 |
| **ECB SDW API** | `https://data-api.ecb.europa.eu/service/data` | 德国 2y 国债收益率 | 月度 |

---

## 1. FRED API 数据获取

### 1.1 美国国债数据（3m, 2y, 10y）

| 内部键名 | FRED 系列代码 | 描述 | 数据频率 |
|----------|---------------|------|----------|
| `us_3m` | `DGS3MO` | 美国 3 个月国债收益率 | 日度 |
| `us_2y` | `DGS2` | 美国 2 年期国债收益率 | 日度 |
| `us_10y` | `DGS10` | 美国 10 年期国债收益率 | 日度 |

**API 调用示例：**
```
GET https://api.stlouisfed.org/fred/series/observations?series_id=DGS3MO&api_key=xxx&observation_start=2000-01-01&observation_end=2026-03-05&file_type=json
```

**历史数据范围：** 从 2000-01-01 开始

---

### 1.2 欧洲国债数据（德国 3m, 10y）

| 内部键名 | FRED 系列代码 | 描述 | 数据频率 |
|----------|---------------|------|----------|
| `eu_3m` | `IR3TIB01DEM156N` | 德国 3 个月银行间利率 | 月度 |
| `eu_10y` | `IRLTLT01DEM156N` | 德国 10 年期国债收益率（OECD） | 月度 |

**API 调用示例：**
```
GET https://api.stlouisfed.org/fred/series/observations?series_id=IRLTLT01DEM156N&api_key=xxx&observation_start=2000-01-01&observation_end=2026-03-05&file_type=json
```

**历史数据范围：** 从 2000-01-01 开始

---

### 1.3 日本国债数据（10y）

| 内部键名 | FRED 系列代码 | 描述 | 数据频率 |
|----------|---------------|------|----------|
| `jp_10y` | `IRLTLT01JPM156N` | 日本 10 年期国债收益率（OECD） | 月度 |

**API 调用示例：**
```
GET https://api.stlouisfed.org/fred/series/observations?series_id=IRLTLT01JPM156N&api_key=xxx&observation_start=2000-01-01&observation_end=2026-03-05&file_type=json
```

**历史数据范围：** 从 2000-01-01 开始

### 1.4 日本国债数据（3m, 2y）- ❌ 暂无可用数据源

| 内部键名 | 数据源 | 描述 | 数据频率 | 状态 |
|----------|--------|------|----------|------|
| `jp_3m` | **暂无** | 日本 3 个月国债收益率 | - | ❌ 无免费稳定 API |
| `jp_2y` | **暂无** | 日本 2 年期国债收益率 | - | ❌ 无免费稳定 API |

**说明：**
- 经过深入调研，**目前没有免费稳定的 API 数据源**可以获取日本 3m/2y 国债收益率数据
- **FRED**：只有 jp_10y 数据（`IRLTLT01JPM156N`），无 3m/2y 数据
- **Trading Economics**：有数据但需要付费订阅，免费版不支持 API 调用
- **Investing.com**：网页有数据但无官方 API，非官方爬虫库（investpy/investiny）不稳定
- **BOJ（日本央行）**：API 已上线但文档未公开，且统计数据库不含国债收益率数据
- **决定**：暂时只保留 jp_10y 数据（FRED 提供），3m/2y 字段留空

**潜在解决方案（供将来参考）：**
1. 付费商业数据源：Trading Economics、Bloomberg、Reuters 等
2. 手动维护：定期从 Investing.com 网页手动下载更新
3. 等待 BOJ：等待日本央行 API 文档公开或增加国债收益率数据

---

### 1.5 汇率数据

| 内部键名 | FRED 系列代码 | 描述 | 数据频率 |
|----------|---------------|------|----------|
| `dollar_index` | `DTWEXBGS` | 美元指数 | 日度 |
| `usd_cny` | `DEXCHUS` | 美元/人民币汇率 | 日度 |
| `usd_jpy` | `DEXJPUS` | 美元/日元汇率 | 日度 |
| `usd_eur` | `DEXUSEU` | 美元/欧元汇率 | 日度（需取倒数） |

**特殊处理：** `usd_eur` 需要取倒数（FRED 提供的是 EUR/USD）

**API 调用示例：**
```
GET https://api.stlouisfed.org/fred/series/observations?series_id=DEXCHUS&api_key=xxx&observation_start=2000-01-01&observation_end=2026-03-05&file_type=json
```

---

## 2. ECB API 数据获取

### 2.1 德国 2 年期国债收益率

| 内部键名 | ECB 系列代码 | 描述 | 数据频率 |
|----------|---------------|------|----------|
| `eu_2y_ecb` | `M.U2.EUR.4F.BB.U2_2Y.YLD` | 德国 2 年期国债收益率 | 月度 |

**API 调用示例：**
```
GET https://data-api.ecb.europa.eu/service/data/FM/M.U2.EUR.4F.BB.U2_2Y.YLD?startPeriod=2021-01-01&endPeriod=2026-03-05&detail=full&format=jsondata
```

**注意事项：**
- ECB API 返回的数据格式为 SDMX JSON
- 时间周期在 `structure.dimensions.observation` 中
- 观测值使用数字索引（"0", "1", "2"...）
- 需要将索引映射到实际时间周期

**历史数据范围：** 约 5 年（超过会导致超时）

---

## 3. 数据保存映射

### CSV 文件结构

| 文件名 | 列名 | 数据来源 | 状态 |
|--------|------|----------|------|
| `us_treasuries.csv` | `美债3m`, `美债2y`, `美债10y` | FRED | ✅ 完整 |
| `eu_bonds.csv` | `德债3m`, `德债2y`, `德债10y` | FRED + ECB | ✅ 完整 |
| `jp_bonds.csv` | `日债10y` | FRED | ⚠️ 部分缺失（3m, 2y 未实现） |
| `exchange_rates.csv` | `美元指数`, `美元人民币`, `美元日元`, `美元欧元` | FRED | ✅ 完整 |

### 内部键名到 CSV 列名的映射

**日本债券映射：**
```python
{
    "jp_10y": "日债10y",    # FRED
    # "jp_3m": "日债3m",    # ❌ 数据源未确定
    # "jp_2y": "日债2y",    # ❌ 数据源未确定
}
```

**欧洲债券映射：**
```python
{
    "eu_3m": "德债3m",      # FRED
    "eu_2y_ecb": "德债2y",  # ECB
    "eu_10y": "德债10y",    # FRED
}
```

---

## 4. API 接口说明

### 4.1 获取历史数据

| 接口 | 数据范围 | 描述 | 数据完整性 |
|------|----------|------|------------|
| `POST /api/macro/fetch/us-treasuries/history` | 2000-01-01 至今 | 获取美债历史数据 | ✅ 3m, 2y, 10y 完整 |
| `POST /api/macro/fetch/eu-bonds/history` | 2000-01-01 至今 | 获取欧债历史数据（3m/10y 从 FRED，2y 从 ECB） | ✅ 3m, 2y, 10y 完整 |
| `POST /api/macro/fetch/jp-bonds/history` | 2000-01-01 至今 | 获取日债历史数据 | ⚠️ 仅 10y（3m, 2y 暂未实现） |
| `POST /api/macro/fetch/exchange-rates/history` | 2000-01-01 至今 | 获取汇率历史数据 | ✅ 所有汇率完整 |

### 4.2 增量更新

| 接口 | 数据范围 | 描述 | 数据完整性 |
|------|----------|------|------------|
| `POST /api/macro/update/us-treasuries` | 最近 7 天 | 增量更新美债数据 | ✅ 3m, 2y, 10y 完整 |
| `POST /api/macro/update/eu-bonds` | 最近 365 天 | 增量更新欧债数据 | ✅ 3m, 2y, 10y 完整 |
| `POST /api/macro/update/jp-bonds` | 最近 365 天 | 增量更新日债数据 | ⚠️ 仅 10y（3m, 2y 暂未实现） |
| `POST /api/macro/update/exchange-rates` | 最近 7 天 | 增量更新汇率数据 | ✅ 所有汇率完整 |

---

## 5. 数据获取流程

### 5.1 日债数据获取流程说明

```python
async def _fetch_jp_bonds(fred_service, start_date, end_date):
    jp_data = {}

    # 从 FRED 获取数据
    # 目前仅支持 10y 期限
    jp_bond_codes = {"jp_10y"}  # ⚠️ jp_3m, jp_2y 数据源未确定

    for name in jp_bond_codes:
        code = settings.fred_codes[name]
        series = await fred_service.fetch_series(code, start_date, end_date)
        jp_data[name] = series

    return jp_data
```

**注意：**
- `jp_3m` 和 `jp_2y` 数据暂无法获取
- 需要调研以下潜在数据源：
  - 日本央行（BOJ）官方统计数据
  - 日本财务省（MOF）发布的数据
  - Bloomberg、Reuters 等金融数据提供商
  - OECD 官方数据库（可能包含更多日本国债数据）

### 5.2 欧债数据获取流程（`_fetch_oecd_bonds`）

```python
async def _fetch_oecd_bonds(fred_service, start_date, end_date):
    oecd_data = {}
    ecb_service = get_ecb_service()

    # 从 FRED 获取数据
    fred_bond_codes = {"eu_3m", "eu_10y", "jp_10y"}
    for name in fred_bond_codes:
        code = settings.fred_codes[name]
        series = await fred_service.fetch_series(code, start_date, end_date)
        oecd_data[name] = series

    # 从 ECB 获取数据
    ecb_bond_codes = {"eu_2y_ecb"}
    for name in ecb_bond_codes:
        series = await ecb_service.fetch_series(name, start_date, end_date)
        oecd_data[name] = series

    return oecd_data
```

### 5.2 ECB 数据获取流程（`ECBService.fetch_series`）

```python
async def fetch_series(name, start_date, end_date):
    # 1. 名称映射到 ECB 代码
    series_key = self.GERMAN_BOND_CODES.get(name, name)
    # 例如: "eu_2y_ecb" -> "M.U2.EUR.4F.BB.U2_2Y.YLD"

    # 2. 构造 API 请求
    url = f"https://data-api.ecb.europa.eu/service/data/FM/{series_key}"
    params = {
        "startPeriod": start_date.strftime("%Y-%m-%d"),
        "endPeriod": end_date.strftime("%Y-%m-%d"),
        "detail": "full",
        "format": "jsondata"
    }

    # 3. 解析 SDMX JSON 响应
    # - 时间周期在 structure.dimensions.observation
    # - 观测值在 dataSets[0].series["0:0:..."].observations
    # - 需要将数字索引映射到时间周期

    return pd.Series(series_data)
```

---

## 6. 关键配置

### FRED 系列代码配置（`src/config.py`）

```python
fred_codes = {
    # 美国国债
    "us_3m": "DGS3MO",
    "us_2y": "DGS2",
    "us_10y": "DGS10",

    # 欧洲国债（德国）
    "eu_3m": "IR3TIB01DEM156N",
    "eu_10y": "IRLTLT01DEM156N",

    # 日本国债
    "jp_10y": "IRLTLT01JPM156N",
}
```

### ECB 系列代码配置（`src/services/ecb_service.py`）

```python
GERMAN_BOND_CODES = {
    "eu_2y_ecb": "M.U2.EUR.4F.BB.U2_2Y.YLD",
    # "eu_5y_ecb": "M.U2.EUR.4F.BB.U2_5Y.YLD",  # 备用
    # "eu_10y_ecb": "M.U2.EUR.4F.BB.U2_10Y.YLD", # 备用（未使用，已有 FRED 数据）
}
```

---

## 7. 注意事项

### ECB API 限制

1. **历史数据范围**：约 5 年，超过会导致请求超时
2. **数据格式**：SDMX JSON，需要特殊解析
3. **时间索引**：使用数字索引，需要映射到时间周期
4. **域名变更**：
   - 旧域名：`sdw-wsrest.ecb.europa.eu`（已废弃，DNS 无法解析）
   - 新域名：`data-api.ecb.europa.eu`

### 数据频率差异

| 数据 | 频率 | 对齐方式 |
|------|------|----------|
| 美债 | 日度 | 前向填充 |
| 德债 3m/10y | 月度（FRED） | 重新索引 + 前向填充 |
| 德债 2y | 月度（ECB） | 重新索引 + 前向填充 |
| 日债 10y | 月度 | 重新索引 + 前向填充 |
| 汇率 | 日度 | 前向填充 |

---

## 8. 错误处理

### API 调用失败

- 所有 API 调用都有重试机制（`@async_retry(max_retries=3, delay=1.0)`）
- 失败时返回空的 `pd.Series(dtype="float64")`
- 错误会记录到日志

### 数据保存

- 使用 `append_data` 方法，自动去重（保留最新数据）
- 如果文件不存在，会自动创建
- 如果数据已存在，会合并并排序

---

## 9. 日债数据调研建议

### 9.1 问题现状
- **日债3m、2y数据缺失**：当前系统只能获取日债10y数据
- **FRED局限性**：在FRED中未找到日本3个月、2年期国债收益率的可靠数据源

### 9.2 潜在数据源调研

#### 9.2.1 日本央行（BOJ）官方数据
- **网站**：https://www.boj.or.jp/
- **统计数据库**：https://www.boj.or.jp/en/statistics/
- **可能提供**：
  - 短期利率（TONAR/TONF）
  - 政府债券收益率曲线
  - 定期发布的金融市场报告

#### 9.2.2 日本财务省（MOF）数据
- **网站**：https://www.mof.go.jp/english/
- **政府债券数据**：https://www.mof.go.jp/english/budget/budget/fy/2024/index.htm
- **可能提供**：
  - 国债拍卖结果
  - 收益率曲线数据
  - 市场统计报告

#### 9.2.3 OECD 官方数据库
- **网站**：https://stats.oecd.org/
- **数据库**：Main Economic Indicators (MEI)
- **可能提供**：
  - 更全面的日本国债数据
  - 不同期限的收益率数据
  - 跨国对比数据

#### 9.2.4 商业金融数据提供商
- **Bloomberg API**：https://www.bloomberg.com/professional/
- **Refinitiv Eikon**：https://www.refinitiv.com/en
- **Wind 万得**：https://www.wind.com.cn/
- **特点**：
  - 数据最全面、最实时
  - 通常需要付费订阅

### 9.3 实施建议

#### 短期方案（1-2个月）
1. **深入调研BOJ数据**
   - 检查是否有可直接调用的API
   - 分析数据格式和获取难度

2. **探索OECD数据库**
   - 确认是否包含日本3m、2y数据
   - 评估数据频率和历史范围

#### 中期方案（3-6个月）
1. **整合BOJ/OECD数据源**
   - 在现有FRED服务基础上新增数据源
   - 保持数据接口的统一性

2. **建立多数据源协调机制**
   - 处理不同数据源的时间差异
   - 确保数据的一致性

#### 长期方案（6个月以上）
1. **商业数据源集成**
   - 评估引入商业数据源的成本效益
   - 可能需要升级数据服务架构

2. **数据质量监控**
   - 建立数据质量检查机制
   - 监控不同数据源的一致性

### 9.4 技术考虑

```python
# 建议的日债数据服务架构
class JPBondService:
    def __init__(self):
        self.fred_service = FREDService()
        self.boj_service = BOJService()  # 待实现
        self.oecd_service = OECDService() # 待实现

    async def fetch_bonds(self, start_date, end_date):
        data = {}

        # FRED数据（已实现）
        data["jp_10y"] = await self.fred_service.fetch_series(...)

        # BOJ数据（待实现）
        # data["jp_3m"] = await self.boj_service.fetch_short_rate(...)
        # data["jp_2y"] = await self.boj_service.fetch_yield_curve(...)

        return data
```

### 9.5 风险评估

| 数据源 | 可靠性 | 更新频率 | 成本 | 实施难度 |
|--------|--------|----------|------|----------|
| FRED | ✅ 高 | 日度/月度 | 免费 | 低 |
| BOJ | ✅ 高 | 月度 | 免费 | 中 |
| OECD | ✅ 高 | 月度 | 免费 | 中 |
| Bloomberg | ✅ 极高 | 实时 | 昂贵 | 高 |

### 9.6 下一步行动

1. **立即行动**：调研BOJ和OECD官方网站的数据可用性
2. **1周内**：确定最合适的数据源
3. **2周内**：设计数据获取方案
4. **1个月内**：实现日债3m、2y数据集成

**注意**：在找到可靠数据源之前，建议：
- 在API响应中明确标注数据缺失情况
- 在前端显示时提示用户数据暂不可用
- 避免返回NaN或null值，保持数据完整性
