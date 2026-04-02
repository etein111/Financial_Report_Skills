# report_maker 设计文档

## 1. 目录结构

```
report_maker/
├── SKILL.md
├── scripts/
│   ├── __init__.py
│   ├── common.py      # 常量、YAML 工具
│   ├── extractor.py   # LLM 要素提取
│   ├── splitter.py    # 摘要/正文拆分
│   └── renderer.py    # 模板渲染 + PDF 转换
└── tests/
    ├── test_extractor.py
    ├── test_splitter.py
    └── test_renderer.py
```

## 2. 核心数据结构

### 报告目录结构

```
reports/<report_name>/
├── draft.docx           # 原始草稿
├── elements.yaml        # 提取的要素（与 schema 一致）
├── abstract.docx        # 摘要片段
├── body.docx            # 正文片段
├── output.docx          # 最终 Word
└── output.pdf           # 最终 PDF
```

### elements.yaml 结构

与 `schema.yaml` 严格保持一致，所有字段都存在（包括空字段）：

```yaml
a1_cn: "杨斌"
a1_email: "harryyang@hfisec.com.hk"
a1_en: "Bin Yang"
a1_sfc: "BSQ313"
abstract: "abstract.docx"
body: "body.docx"
company: "西锐飞机"
current_price: ""
current_price_date: ""
market_cap: ""
one_year_high: ""
one_year_low: ""
rating: "OUTPERFORM"
report_date: "21 Oct 2025"
shares_in_issue: ""
target_price: "86.72"
ticker: "2507.HK"
title: "首次覆盖：安全..."
```

**注意**：
- 字段名与 `schema.yaml` 中的键名完全一致
- 空字段使用空字符串 `""`
- `abstract` 和 `body` 的值为文件路径引用
- 第一阶段中，`source: market` 的字段允许保持为空
- 第二阶段刷新市场数据成功后会回写 `elements.yaml`，因此 `elements.yaml` 既是中间状态，也是最终渲染快照

### schema.yaml 字段约定

第一版在原有字段定义上只新增一个 `source` 元信息，用于区分字段来源；`type` 继续仅用于描述特殊字段形态：

```yaml
company:
  description: 公司名称
  format: 西锐飞机
  source: draft

ticker:
  description: 股票代码
  format: 2507.HK
  source: draft

current_price:
  description: 当前价格
  format: "60.40"
  source: market

current_price_date:
  description: 当前价格日期
  format: 2026 年 01 月 15 日
  source: market

abstract:
  description: 报告摘要部分
  type: fragment
  scope: 首页右侧
  source: draft
```

**约定**：
- `source` 第一版只允许 `draft` 和 `market`
- `source: draft`：第一阶段从草稿提取或拆分
- `source: market`：第一阶段不提取，先保留为空；第二阶段按 `ticker` 自动刷新
- `type: fragment`：仅用于 `abstract`、`body` 等 Word 片段字段
- 普通短字段不需要显式声明 `type`，默认视为标量字段
- 中文模板和英文模板使用各自独立的 `schema.yaml`，日期和数字展示格式直接体现在对应模板的 `format` 示例中
- 第一版不引入 `render_required`、`required_fields`、`render` 等额外配置

## 3. 两阶段流程

### 第一阶段：抽取与确认（交互式）

**LLM 决策 + Python 执行**

```python
# 1. 接收草稿和报告类型（人工指定）
report_type = "company"  # 用户指定
draft_path = save_draft(file)

# 2. 获取模板名
template_name = get_template(report_type)  # 从 router.yaml

# 3. 创建报告目录
report_dir = f"reports/{report_name}/"
os.makedirs(report_dir)

# 4. 加载 schema
schema = load_yaml(f"templates/{template_name}/schema.yaml")

# 5. 只提取 source: draft 且非 fragment 的字段
draft_schema = {
    field_name: field_schema
    for field_name, field_schema in schema.items()
    if field_schema.get("source", "draft") == "draft"
    and field_schema.get("type") != "fragment"
}
elements = extract_elements(draft_path, draft_schema)

# 6. 确保所有字段都存在（包括 source: market 的空字段）
for field_name in schema.keys():
    if field_name not in elements:
        elements[field_name] = ""

# 7. 交互式确认 source: draft 的普通字段
for field_name in draft_schema.keys():
    extracted_value = elements.get(field_name, "")

    # 展示并确认
    print(f"{field_name}: {extracted_value}")

    if not extracted_value:
        # LLM 未提取到，询问用户
        user_input = input(f"未提取到 {field_name}，留空吗？(直接回车留空，或输入值): ")
        elements[field_name] = user_input if user_input else ""
    else:
        # LLM 提取到了，让用户确认
        confirm = input("确认？(y/n/修改): ")
        if confirm == 'n':
            elements[field_name] = ""
        elif confirm.startswith('修改'):
            new_value = confirm.split(' ', 1)[1] if ' ' in confirm else ""
            elements[field_name] = new_value

# 8. 保存第一阶段结果
save_yaml(f"{report_dir}/elements.yaml", elements)

# 9. 拆分摘要和正文（type: fragment）
abstract_doc = extract_abstract(draft_path, schema['abstract']['scope'])
body_doc = extract_body(draft_path, schema['body']['scope'])
abstract_doc.save(f"{report_dir}/abstract.docx")
body_doc.save(f"{report_dir}/body.docx")

# 10. 展示摘要并等待用户确认继续
# source: market 的字段此时仍为空，进入第二阶段前再刷新
show_summary(elements)
```

### 第二阶段：渲染与输出

**纯 Python 实现**

```python
# 1. 更新修正后的 elements
elements = load_yaml(f"{report_dir}/elements.yaml")
elements.update(corrections)

# 2. 按 ticker 刷新 source: market 的字段
market_elements = refresh_market_data(
    ticker=elements["ticker"],
    schema=schema,
)
elements.update(market_elements)
save_yaml(f"{report_dir}/elements.yaml", elements)

# 3. 渲染短字段（Jinja2）
template = DocxTemplate(f"templates/{template_name}/template.docx")
template.render(elements)

# 4. 插入长文本片段（python-docx）
insert_fragment(template.doc, elements['abstract'])
insert_fragment(template.doc, elements['body'])

# 5. 保存 output.docx
template.save(f"{report_dir}/output.docx")

# 6. 转换 PDF
convert_to_pdf(f"{report_dir}/output.docx", f"{report_dir}/output.pdf")
```

**补充说明**：
- `current_price`、`current_price_date`、`market_cap`、`shares_in_issue`、`one_year_high`、`one_year_low` 等字段属于 `source: market`
- 这类字段不再作为第一阶段正式提取目标
- 第二阶段刷新成功后统一回写 `elements.yaml`
- 刷新失败时由刷新流程自然报错并中止，不额外增加配置化校验体系

### 第二阶段：市场数据刷新细节

第一版市场数据直接使用 `yfinance` 获取，不额外抽象 `market_data_provider` 层。后续如需切换数据源，统一修改刷新逻辑即可。

#### ticker 规范化

在调用 `yfinance` 前，先将模板中的 `ticker` 规范化为 Yahoo Finance 可识别格式：

- 港股：
  - `700 HK` -> `0700.HK`
  - `700.HK` -> `0700.HK`
  - `2507.HK` -> `2507.HK`
- 美股：
  - `VST US` -> `VST`
  - `MSFT US` -> `MSFT`
  - `VST` -> `VST`
- 美股带点号类别：
  - `BRK.B US` -> `BRK-B`
  - `BF.B` -> `BF-B`

建议逻辑：
- 去掉首尾空格
- 将连续空格压缩为单个空格
- 转为大写
- 港股代码抽取数字部分并左侧补零到 4 位，再拼接 `.HK`
- 美股代码去掉尾部 `US` 标记，并将 `.` 转为 `-`

#### 字段获取口径

价格相关字段统一从日线历史中计算，口径固定为“收盘价”：

```python
stock = yf.Ticker(normalized_ticker)
history = stock.history(
    period="1y",
    interval="1d",
    auto_adjust=False,
    actions=False,
)
```

说明：
- `auto_adjust=False`，确保使用未复权价格
- 不使用盘中价或 `regularMarketPrice`
- 不直接依赖 `info` 中的 52 周高低点，而是自己从日线历史计算

#### 6 个市场字段的计算方式

- `current_price`：最后一个有效交易日的 `Close`
- `current_price_date`：最后一个有效交易日的日期
- `one_year_high`：`history["High"].max()`
- `one_year_low`：`history["Low"].min()`
- `market_cap`：优先 `fast_info["market_cap"]`，其次 `info["marketCap"]`
- `shares_in_issue`：优先 `info["sharesOutstanding"]`

如果 `market_cap` 缺失，但 `shares_in_issue` 和 `current_price` 都可用，则可使用：

```python
market_cap = current_price * shares_in_issue
```

#### 格式化约定

刷新得到原始值后，在回写 `elements.yaml` 前统一格式化为模板可直接消费的字符串：

- `current_price`、`one_year_high`、`one_year_low`：保留 2 位小数
- `current_price_date`：按对应模板 `schema.yaml` 中的日期示例格式输出
- `market_cap`：写为 `22.11bn` 这类展示字符串
- `shares_in_issue`：写为 `365.99mn` 这类展示字符串

因此，`elements.yaml` 中保留的是最终展示值，而不是原始数值对象

### 第二阶段：首页股价图刷新

第一版只实现首页股价图，不实现 `recommendation_chart`。

#### 模板占位符

首页股价图改为模板图片占位符方式，在 `Table_Info` 的图片区使用：

```text
{{ stock_price_chart }}
```

约定如下：
- 删除 `Table_Info` 中原有的两张示例图片
- 将原股价图和成交量图区域合并为一个图片区
- 在该图片区单独放置 `{{ stock_price_chart }}`
- 占位符单独占据一个段落或一个表格单元格，不与其他文字混排

`Table_RecommendationChart` 暂不纳入第一版实现，保持现状。

#### 图像生成与插入

首页股价图采用以下技术组合：

- 图像生成：`matplotlib`
- 模板插图：`docxtpl.InlineImage`

渲染时：
- 先用 `matplotlib` 生成 `reports/<report_name>/assets/stock_price_chart.png`
- 再在 `template.render(context)` 前，将 `context["stock_price_chart"]` 设置为 `InlineImage`

示意：

```python
context["stock_price_chart"] = InlineImage(
    template,
    str(chart_path),
    width=Mm(63.5),
)
```

#### 图像内容

首页股价图为一张合成图，不再拆分为单独的股价图和成交量图：

- 上半部分：股价折线图
- 下半部分：成交量柱状图
- 两部分共用同一条时间轴

数据口径：
- 时间范围：`1y`
- 价格：最近一年未复权日线收盘价
- 成交量：同一时期日线成交量

#### 视觉规格

第一版首页股价图的默认视觉规格如下：

- 画布：白底
- 结构：上下两个子图，共用 x 轴
- 高度比例：价格区 `3`，成交量区 `1`
- 价格线：深蓝色实线，线宽 `1.6 - 2.0`
- 成交量柱：浅蓝灰色柱状图，无额外边框
- 网格：只保留浅灰色横向网格，不显示竖向网格
- 边框：去掉上边框和右边框，保留左边和下边的浅灰轴线
- x 轴：按月显示刻度
- y 轴：保留简洁刻度，不做过度装饰
- 字体：优先使用运行环境默认可用字体，不额外依赖复杂字体安装
- Source 文本：放在模板外，不画入图片；继续使用模板中的 `资料来源： {{ source }}`
- 输出格式：PNG

#### 设计目标

首页股价图的目标是：

- 与历史报告中的图保持信息结构一致
- 在视觉风格上尽量接近
- 保证自动化批量生成稳定

第一版不追求与历史图逐像素一致。

## 4. 模块职责

| 模块 | 职责 |
|------|------|
| **common.py** | 常量定义、YAML 工具函数（与 template_maker 共享） |
| **extractor.py** | LLM 要素提取，基于 schema.yaml 约束 |
| **splitter.py** | 摘要/正文拆分，基于 schema 中的 scope 描述 |
| **renderer.py** | 第二阶段数据合成、ticker 规范化、市场数据刷新、首页股价图生成、模板渲染（Jinja2）+ 片段插入 + PDF 转换 |

### 关键函数接口

```python
# common.py
load_yaml(path) -> dict
save_yaml(path, data) -> None
get_template(report_type) -> str  # 从 router.yaml 获取模板名

# extractor.py
extract_elements(draft_path, schema) -> dict  # LLM 提取

# splitter.py
extract_abstract(draft_path, scope) -> Document
extract_body(draft_path, scope) -> Document

# renderer.py
normalize_ticker_for_yfinance(raw_ticker) -> str
refresh_market_data(ticker, schema) -> dict
generate_stock_price_chart(price_history, volume_history, output_path) -> str
render_and_save(template_path, elements, abstract_path, body_path, output_dir) -> None
```

## 5. 与 template_maker 的协作

```
template_maker                    report_maker
     |                                |
     v                                v
templates/                        reports/
├── router.yaml  <-------------- 读取路由
├── company/                      |
│   ├── schema.yaml  <--------- 读取提取规则
│   └── template.docx  <------- 读取并渲染
```

### 边界原则

- report_maker **只读** `templates/`
- report_maker **只写** `reports/`
- 不修改任何模板资产

### 数据流向

```
router.yaml -> 报告类型 -> 模板名
schema.yaml -> 字段来源约定(source/type)
draft.docx + schema.yaml -> 第一阶段提取 draft 字段 + 片段拆分 -> elements.yaml
ticker + 行情数据源 -> 第二阶段刷新 market 字段 -> elements.yaml
template.docx + elements.yaml + abstract.docx + body.docx -> output.docx
```

## 6. 设计要点总结

1. **目录结构简洁**：4 个核心模块
2. **数据结构严格一致**：elements.yaml 与 schema.yaml 字段名完全对应
3. **两阶段流程**：
   - 第一阶段：只提取 `source: draft` 字段，并拆分 `type: fragment` 片段
   - 第二阶段：先刷新 `source: market` 字段并回写 `elements.yaml`，再进行纯 Python 确定性渲染
4. **与 template_maker 清晰隔离**：只读 templates/，只写 reports/
5. **空字段处理**：所有字段都存在；`source: market` 字段在第一阶段允许为空
6. **最终快照原则**：`elements.yaml` 在第二阶段刷新后作为最终渲染快照保留
7. **价格口径统一**：市场价格字段统一使用最近有效交易日的未复权收盘价
8. **首页图表策略**：首页股价与成交量合成为一张图片，通过 `{{ stock_price_chart }}` 插入模板
