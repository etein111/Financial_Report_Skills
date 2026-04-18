# Report Maker 测试过程记录 - test_en

## 测试信息
- 测试日期: 2026/04/18
- 输入文件: samples/EN-Vistra Corp20260104.docx
- 报告类型: company
- 语言: en

## 第一阶段：抽取与确认

### 1. 预处理
- 提取文档表格内容（使用 lxml 解析嵌套表格）
- 提取文档段落（带位置索引）
- 表格内容显示：封面包含完整字段信息

### 2. LLM 字段提取
提取结果：
- report_date: 5 Jan 2026
- company_en: Vistra Corp
- ticker: VST US
- title: Active Response to Energy Transition and Enhancement of Low-Carbon Power Amid AI Data Center Migration and Natural Gas Demand Growth: Initiation
- rating: OUTPERFORM
- current_price: 356.36
- current_price_date: 12 Dec 2025
- market_cap: 17.842bn
- shares_in_issue: 45.69mn
- one_year_high: 451.28
- one_year_low: 158.08
- target_price: 423.72
- source: Company data, HFI
- a1_en: Bin Yang
- a1_email: harryyang@hfisec.com.hk

### 3. 位置信息
- has_abstract: false（英文报告通常无 abstract）
- has_body: true
- body_start_marker: "1. Vistra: Major Fortune 500 player in the U.S. energy market"
- body_end_marker: "Electricity demand is lower than expected; Natural gas rise beyond expectation; Changes in regulatory policies."
- has_english_summary: false（英文报告不需要英文摘要）

### 4. 提取结果
- abstract.docx: 7 段落（从首页表格 Row8 Cell1 提取的投资亮点）
- body.docx: 176 段落, 31 表格

## 第二阶段：渲染与输出

### 1. 模板
- 模板路径: templates/company/en/template.docx

### 2. 渲染步骤
1. 加载模板
2. 替换占位符（company, title, rating, target_price, current_price, market_cap, report_date, ticker, a1_*）
3. 插入 body（使用 docxcompose.append）

### 3. 输出文件
- Vistra Corp(VST US)：Active Response to Energy Transition - Initiation_v2.docx（最新完整版）
- 段落数: 182
- 表格数: 33
- 图片数: 36（含 relative_chart 和 recommendation_chart）
- 验证: 无未填充占位符，封面表格包含 abstract (3921 chars)

## 目录结构
```
test_en/
├── draft.docx              # 原始草稿
├── elements.yaml           # 提取的要素
├── abstract.docx           # 投资亮点摘要（7段落）
├── body.docx              # 正文片段（176段落，31表格）
├── relative_chart.png      # 相对收益图
├── recommendation_chart.png # 推荐走势图
└── Vistra Corp(VST US)：Active Response to Energy Transition - Initiation_v2.docx  # 最终输出
```

## 备注
- 使用 `.venv/Scripts/python.exe` + 7890 代理渲染
- relative_chart.png (133KB) 生成成功
- recommendation_chart.png (45KB) 生成成功（无历史推荐数据，仅价格线）
- 注意：VST US ticker 在 yfinance 中查询 404，使用 VST 查询成功
