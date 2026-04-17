# Agent Req

## 目标与定位

工作台的自动化逻辑，实现 AI 自动编辑和审核：研报模板刷新、自动翻译、评级变动审批、合规检查（StockList 等）。

将自动化逻辑按独立 Agent Skills 组织，彼此解耦，通过可定制的流程编排触发。

## 报告类型

| 报告类型 | 说明 | 常用模板 |
|---------|------|----------|
| `company` | 公司覆盖报告（首次覆盖、深度分析等） | company |
| `sector` | 行业研究报告 | sector |
| `company_flash` | 公司快讯 | company_flash |
| `sector_flash` | 行业快讯 | sector_flash |
| `macro` | 宏观报告 | common |
| `strategy` | 策略报告 | common |
| `quantitative` | 量化报告 | common |
| `bond` | 债券报告 | common |

## 报告创建流程

```
上传文件 → 字段检查 → 文件检查 → 相似度检查 → SFC 检查
→ Coverage 检查 → 标题生成 → 提交报告 → RQC/首席审批 → 发布
```

## Capabilities

### 检查报告基本信息

检查报告类型所需的字段是否完整，自动从原始报告提取要素，不齐则提示补齐。

字段提取示例：

| 字段 | 来源 |
|------|------|
| Ticker | 报告内容 |
| Rating | 报告内容 |
| Target price | 报告内容 |
| Region | 报告内容 |
| Sector | 报告内容 |
| Report language | 报告内容 |
| Report title | 表格第6行1列 |
| Analysts | 分析师名字、邮箱（多个都提取） |
| Contact Person | 工作台输入或 neolyst 选择 |
| Investment thesis | 报告首页表格第9行2列，可能跨页需人工干预 |

### 检查文件齐全性

- 所有报告必须有 Word 文件
- Company 报告必须有 Model 文件

### 检查报告数据与 Model 一致性（优先级低）

自动提取报告中的数据（如盈利预测）与 Model 比对，不一致则提示修改。

### 检查文件相似度，防止提交错文件

比对文件名与上一版最新文件名的相似度。相似度 < 60% 时警告。

算法：`1 - 莱文斯坦距离 / 最大字符串长度`。

### 保存报告基本信息

自动从原始报告提取要素，缺少的与人沟通补齐，自动在 neolyst 新建草稿报告。

### 检查 Sector 是否存在

不存在则提醒。

### Sector 选择及新建（优先级低）

两级结构。系统已有行业可供选择；不满足时，分析师提供一级/二级、中/英文名称后新建。

### Coverage 审批

检查报告的 Coverage 是否已存在，不存在则提示在 neolyst 中添加。

### Company 报告标题自动生成

规则：

| 场景 | 格式 | 示例 |
|------|------|------|
| 首次覆盖 | `{公司名} ({Ticker}): 首次覆盖: {标题}` | Vertiv (VRT US)：首次覆盖：报告标题 |
| 评级变动，目标价不变 | `{公司名} ({Ticker}): {标题}—{动作}{评级}` | Vertiv (VRT US)：报告标题—上调至优于大市 |
| 评级+目标价变动 | `{公司名} ({Ticker}): {标题}—{动作}{评级}; {TP动作}{TP变动}%` | Vertiv (VRT US)：报告标题—上调至优于大市; 上调目标价24% |
| 仅目标价变动 | `{公司名} ({Ticker}): {标题}—维持{评级}; {TP动作}{TP变动}%` | Vertiv (VRT US)：报告标题—维持优于大市; 上调目标价24% |
| 评级和目标价都不变 | `{公司名} ({Ticker}): {标题}—维持{评级}` | Vertiv (VRT US)：报告标题—维持优于大市 |
| 有英文版标题 | `公司中文简称 ({Ticker}): 中文标题—动作评级; TP动作 (English Title — Action & TP)` | 腾讯控股 (700 HK)：报告标题—上调至优于大市; 上调目标价24%（Tencent：English Title—Maintain OP & Raise TP by 24%） |

### StockList（优先级低）

1. 脱敏处理（隐藏评级、目标价、敏感词）
2. 发送脱敏报告给大模型提取所有公司
3. 匹配上市公司 code，未匹配的为非上市公司
4. 生成 stock list 发给合规部门
5. 合规回复 excel（利益披露信息）
6. Run disclosure 生成披露文字
7. 有披露内容则贴到报告附录

### 核对分析师与 SFC 署名

- 从 https://apps.sfc.hk/publicregWeb/searchByName 查询 SFC 牌照
- 自动填充到 report 中
- 遇重名等特殊情况与人确认
- 报告署名 Analyst 必须有 SFC，无 SFC 禁止发布
- 提交时自动检查，无 SFC 阻断 submit

### 提取报告摘要和正文

自动从 Word 内容中提取摘要和正文。

### 生成股价图

从市场数据库取出 ticker 数据生成图表：

- **股价走势图**：最近一年股票收盘价与指数收盘价的涨跌幅。起点固定为 100，后续按日涨跌幅累乘
- **Volume 柱状图**：股票 Volume 数据柱状图

### 生成报告（先只做 Company）

Company 报告模板填充规则：

| 位置 | 内容 | 数据源 |
|------|------|--------|
| 表格 Table_Main 第3行1列 | 报告日期 | 当前日期，格式：4 Feb 2026 |
| 表格 Table_Main 第5行1列 | 公司+股票代码 | coverage 表 english_full_name、chinese_short_name、ticker |
| 表格 Table_Main 第5行1列 | 标题 | 分析师输入（中英文换行区分） |
| 表格 Table_Info 第2行1列 | 评级调整 | 对比上一次报告 Rating 与本次 Rating |
| 表格 Table_Info 第4行2列 | 评级 | 分析师输入 → report.rating |
| 表格 Table_Info 第5行2列 | 现价 | 股票最新收盘价 |
| 表格 Table_Info 第6行2列 | 目标价 | 分析师输入 → report.target_price |
| 表格 Table_Info 第7行2列 | 市值 | 股票行情数据 |
| 表格 Table_Info 第8行2列 | 发行股票数目 | 股票行情数据 |
| 表格 Table_Info 第9行2列 | 1年股价最高最低值 | 股票行情数据 |
| 表格 Table_Info 第10行1列 | Note | `Note: Current Price {close_price} is the close price on {date}` |
| 表格 Table_Info 第12行1列 | 股价走势图 | 股票行情+指数行情数据 |
| 表格 Table_Info 第13行1列 | Volume 柱状图 | 股票行情数据 |
| 表格 Table_Author 第2行起 | 分析师信息 | 分析师姓名、SFC 编号、邮箱，每行一位，最多 8 位 |
| 表格 Table_header1 第2行 | 页眉 | Company + Code；评级调整 |
| 表格 Table_disclaimer 第4行1列 | 附录 Analyst Certification | `I, {analyst_name}, certify that...`，每位分析师一行 |

生成后自动上传 neolyst。

### 报告提交

提交前检查：RQC 是否通过、首席是否通过、Coverage 是否存在等。检查通过后自动在 neolyst 提交报告。

## RQC 触发条件

- 首次覆盖
- 评级变动
- 目标价变动 ≥ 30%
