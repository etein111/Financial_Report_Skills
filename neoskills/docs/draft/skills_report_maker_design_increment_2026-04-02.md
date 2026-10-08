# report_maker 设计增量记录（2026-04-02）

## 1. 背景

本次增量只处理一个问题：公司类模板中的股票市场数据如何自动刷新并进入最终报告。

讨论结论是，问题的核心不在 Word 模板本身，而在 `report_maker` 的两阶段流程：
- 第一阶段负责草稿理解、字段确认和片段拆分
- 第二阶段负责按 `ticker` 刷新市场数据，并将刷新结果写回 `elements.yaml` 后再渲染模板

## 2. 本次确认的设计结论

### 2.1 市场字段不作为第一阶段正式提取目标

以下字段改为在第二阶段按 `ticker` 自动刷新：

- `current_price`
- `current_price_date`
- `market_cap`
- `shares_in_issue`
- `one_year_high`
- `one_year_low`

第一阶段中，这些字段在 `elements.yaml` 里允许为空。

### 2.2 `schema.yaml` 只新增 `source`

第一版只新增一个字段来源标记：

- `source: draft`：从草稿提取或拆分
- `source: market`：渲染前刷新

`type` 继续只负责表示字段形态，第一版仍主要用于：

- `type: fragment`

普通短字段不需要显式声明 `type`。

### 2.3 中英文模板使用不同 schema

中文版和英文版报告使用不同的模板与 `schema.yaml`。  
因此日期和数字展示差异，不在同一个 schema 中做多语言分支，而是分别在各自模板的 `format` 示例中体现。

### 2.4 `elements.yaml` 作为最终渲染快照

`elements.yaml` 不再只是草稿提取结果，也承担最终渲染快照的角色：

- 第一阶段写入草稿提取结果
- 第二阶段刷新市场字段后再次回写
- `output.docx` 和 `output.pdf` 使用回写后的 `elements.yaml` 渲染

这样可以保证最终文档与落盘数据一致，便于审计和复现。

### 2.5 刷新失败时自然阻断

第一版不增加额外的配置化校验体系。

约定如下：
- `source: market` 的字段刷新失败时，由刷新流程自然报错并中止
- 不引入 `render_required`
- 不引入模板级 `required_fields`
- 不新增额外的格式 DSL

### 2.6 市场数据源与 ticker 规范化

第一版市场数据直接使用 `yfinance` 获取，不额外抽象 `market_data_provider` 层。

在调用 `yfinance` 前，先将 `ticker` 规范化为 Yahoo Finance 可识别格式：

- 港股：
  - `700 HK` -> `0700.HK`
  - `700.HK` -> `0700.HK`
  - `2507.HK` -> `2507.HK`
- 美股：
  - `VST US` -> `VST`
  - `MSFT US` -> `MSFT`
- 美股带点号类别：
  - `BRK.B US` -> `BRK-B`
  - `BF.B` -> `BF-B`

规范化逻辑只做最小支持：
- 清理空格
- 统一大写
- 港股代码补零到 4 位并拼接 `.HK`
- 美股代码去掉尾部 `US`
- 美股类别名中的 `.` 转为 `-`

### 2.7 市场字段取值口径

价格相关字段统一从 `yfinance` 的日线历史中计算，固定口径为“收盘价”：

- 使用 `history(period="1y", interval="1d", auto_adjust=False, actions=False)`
- `current_price`：最后一个有效交易日的 `Close`
- `current_price_date`：最后一个有效交易日的日期
- `one_year_high`：一年日线中的 `High.max()`
- `one_year_low`：一年日线中的 `Low.min()`
- `market_cap`：优先 `fast_info["market_cap"]`，其次 `info["marketCap"]`
- `shares_in_issue`：优先 `info["sharesOutstanding"]`

如 `market_cap` 缺失，但 `shares_in_issue` 与 `current_price` 可用，则允许用两者乘积兜底。

### 2.8 回写前格式化

刷新得到原始值后，先格式化，再回写 `elements.yaml`：

- `current_price`、`one_year_high`、`one_year_low`：保留 2 位小数
- `current_price_date`：按对应模板 `schema.yaml` 的日期示例格式输出
- `market_cap`：写为 `22.11bn` 这类展示字符串
- `shares_in_issue`：写为 `365.99mn` 这类展示字符串

因此 `elements.yaml` 存储的是最终展示值，而不是原始数值对象。

### 2.9 首页股价图方案

第一版只实现首页股价图，不实现 `recommendation_chart`。

模板改为图片占位符方式，在 `Table_Info` 的图片区使用：

```text
{{ stock_price_chart }}
```

约定如下：
- 删除 `Table_Info` 中原有两张示例图片
- 将原股价图和成交量图区域合并为一个图片区
- 在该区域单独放置 `{{ stock_price_chart }}`
- 占位符单独占一个段落或单元格，不与其他文字混排

图像技术方案：
- 图像生成：`matplotlib`
- 模板插图：`docxtpl.InlineImage`

生成流程：
- 根据最近一年日线数据生成一张合成图
- 图内容为：上半部分股价折线，下半部分成交量柱状图
- 输出为 `reports/<report_name>/assets/stock_price_chart.png`
- 在模板渲染时通过 `InlineImage` 注入 `{{ stock_price_chart }}`

### 2.10 首页股价图视觉规格

第一版默认视觉规格如下：

- 白底
- 上下双子图，共用 x 轴
- 高度比例 `3:1`
- 价格线为深蓝色实线
- 成交量柱为浅蓝灰色
- 仅保留浅灰色横向网格
- 去掉上边框和右边框
- x 轴按月显示刻度
- Source 文本不画进图中，继续由模板外部文字承载
- 输出 PNG

设计目标是与历史图保持结构和风格接近，并保证自动化稳定生成；第一版不追求逐像素一致。

## 3. 不纳入本次增量的内容

以下内容本次明确不做：

- 不在 schema 中增加 `render_required`
- 不在 `meta.yaml` 中增加 `required_fields`
- 不新增 `render` 配置
- 不对第一阶段的普通草稿字段增加新的强制校验体系
- 不额外抽象 `market_data_provider` 层
- 不在第一版实现 `recommendation_chart`

这些能力如后续确有需要，再基于真实问题补充。

## 4. 对主设计稿的影响

主设计稿需要同步体现以下变化：

- 第一阶段只处理 `source: draft`
- `type: fragment` 的字段继续单独拆分
- 第二阶段新增市场数据刷新并回写 `elements.yaml`
- `elements.yaml` 的语义更新为“中间状态 + 最终渲染快照”
