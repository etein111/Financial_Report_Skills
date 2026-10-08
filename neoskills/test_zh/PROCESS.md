# Report Maker 测试过程记录 - test_zh

## 测试信息
- 测试日期: 2026/04/18
- 输入文件: inbox/samples/company/0402威胜控股（3393.HK）首次覆盖：配网投资与AI算力双轮驱动，能源计量龙头再启航.docx
- 报告类型: company
- 语言: zh

## 第一阶段：抽取与确认

### 1. 预处理
- 提取文档表格内容（使用 lxml 解析嵌套表格）
- 提取文档段落（带位置索引）
- 表格内容显示：封面包含完整字段信息

### 2. LLM 字段提取
提取结果：
- report_date: 2 Apr 2026
- company_cn: 威胜控股
- company_en: Wasion Holdings
- ticker: 3393.HK
- title: 首次覆盖：配网投资与AI算力双轮驱动，能源计量龙头再启航
- a1_cn: 杨斌
- a1_en: Bin Yang
- a1_email: harryyang@hfisec.com.hk
- a1_sfc: BSQ313
- a2_cn: 邓轶达
- a2_en: Yida Deng
- a2_email: dengyida@hfisec.com.hk
- a2_sfc: BVF321

### 3. 位置信息
- has_abstract: false（报告无正式摘要，封面表格中包含投资亮点）
- has_body: true
- body_start_marker: "1 威胜控股：能源计量与能效管理专家"
- body_end_marker: "国家电网及南方电网集采招标量价不及预期；海外市场业务增长速度慢于预期；海外生产成本上升"
- has_english_summary: true
- english_summary_scope: P275-P291

### 4. 提取结果
- abstract.docx: 8 段落（从首页表格 Row8 Cell1 提取的投资亮点）
- body.docx: 272 段落, 26 表格
- english_summary.docx: 19 段落, 0 表格

## 第二阶段：渲染与输出

### 1. 模板
- 模板路径: templates/company/zh/template.docx

### 2. 渲染步骤
1. 加载模板
2. 替换占位符（company, title, rating, target_price, current_price, market_cap, report_date, ticker, a1_*, a2_*）
3. 插入 body（使用 docxcompose.append）
4. 插入 english_summary（追加到文档末尾）

### 3. 输出文件
- 威胜控股(3393.HK)：首次覆盖 - 配网投资与AI算力双轮驱动_v2.docx（最新完整版）
- 段落数: 290
- 表格数: 28
- 图片数: 31（含 relative_chart 和 recommendation_chart）
- 验证: 无未填充占位符，封面表格包含 abstract (839 chars)

## 目录结构
```
test_zh/
├── draft.docx              # 原始草稿
├── elements.yaml           # 提取的要素
├── abstract.docx           # 投资亮点摘要（8段落）
├── body.docx              # 正文片段（272段落，26表格）
├── english_summary.docx    # 英文摘要片段（19段落）
├── relative_chart.png      # 相对收益图
├── recommendation_chart.png # 推荐走势图
└── 威胜控股(3393.HK)：首次覆盖 - 配网投资与AI算力双轮驱动_v2.docx  # 最终输出
```

## 备注
- 使用 `.venv/Scripts/python.exe` + 7890 代理渲染
- relative_chart.png (96KB) 和 recommendation_chart.png (53KB) 生成成功
- relative_chart 已插入文档
- recommendation_chart 已插入文档（含 2 条历史推荐数据）
- 法律附录保留完整
- 输出: 段落=290, 表格=28, 图片=31
