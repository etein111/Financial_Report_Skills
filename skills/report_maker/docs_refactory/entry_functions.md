# report_maker 入口函数表

  ┌───────────────┬─────────────────────────────┬───────────────────────────────────┐
  │     步骤      │          入口函数           │               结果                │
  ├───────────────┼─────────────────────────────┼───────────────────────────────────┤
  │ 1.5 预处理    │ preprocess_for_extraction() │ 547 行输出 ✅                     │
  ├───────────────┼─────────────────────────────┼───────────────────────────────────┤
  │ 1.8 提取摘要  │ extract_abstract()          │ 39KB ✅                           │
  ├───────────────┼─────────────────────────────┼───────────────────────────────────┤
  │ 1.8 提取正文  │ extract_body()              │ 1.6MB ✅                          │
  ├───────────────┼─────────────────────────────┼───────────────────────────────────┤
  │ 1.10 保存字段 │ save_yaml()                 │ 54 字段 ✅                        │
  ├───────────────┼─────────────────────────────┼───────────────────────────────────┤
  │ 2.3 渲染      │ render_from_dir()           │ 1.6MB, 256段落, 41表格, 29图片 ✅ │
  ├───────────────┼─────────────────────────────┼───────────────────────────────────┤
  │ 2.4 验证      │ verify_no_placeholders()    │ True ✅                           │
  └───────────────┴─────────────────────────────┴───────────────────────────────────┘



基于 `cirrus(2507)_20251021` 样本报告的完整流程记录。

## 调用顺序

| 步骤 | 文件 | 入口函数 | 模块 | 输出大小 |
|------|------|---------|------|---------|
| 1.4 加载模板 | — | `resolve_template_for_report()` | `neolyst_integration` | — |
| 1.5 预处理 | `01_preprocess.txt` | `preprocess_for_extraction()` | `docx_reader` | 88KB |
| 1.8 提取摘要 | `02_abstract.docx` | `extract_abstract()` | `splitter` | 39KB |
| 1.8 提取正文 | `03_body.docx` | `extract_body()` | `splitter` | 1.6MB |
| 1.8 提取英文摘要 | — | `extract_english_summary()` | `splitter` | — |
| 1.10 保存字段 | `04_elements.yaml` | `save_yaml()` | `common` | 1KB |
| 1.11 保存草稿 | — | `save_report()` | `neolyst` | — |
| 4b 准备草稿 | — | `prepare_and_save_draft()` | `workflow` | — |
| 4b 提交报告 | — | `submit_report_workflow()` | `workflow` | — |
| 4b 解析 coverage | — | `resolve_coverage()` | `neolyst_integration` | — |
| 2.3 渲染 | `05_rendered_report.docx` | `render_from_dir()` / `render_report()` | `renderer` | 1.6MB |
| 2.4 验证 | `06_verify.txt` | `verify_no_placeholders()` | `post_processor` | 64B |
| 2.5 转 PDF | — | `word2pdf convert`（CLI） | — | — |

## 数据流

```
preprocess_for_extraction()  →  print 到对话上下文  →  LLM 提取字段和标记
                                                           ↓
extract_abstract()  ←  start_marker / end_marker
extract_body()      ←  start_marker / end_marker
extract_english_summary()  ←  start_marker / end_marker
        ↓
save_yaml()  →  elements.yaml
        ↓
render_from_dir()  →  内部调用 render_report()  →  最终报告
        ↓
verify_no_placeholders()  →  确认无 {{}} 残留
```

## render_report() 内部调用链

- `context.prepare_context_with_analysts()` — 展开分析师字段
- `placeholder_fixer._fix_split_placeholders_in_docx()` — 修复拆分占位符
- `chart_generator._generate_relative_chart()` — 相对收益对比图
- `chart_generator._generate_recommendation_chart()` — 推荐走势图
- `docxtpl.DocxTemplate.render()` — 模板变量替换
- `content_inserter.insert_abstract_to_cell()` — 插入摘要到表格
- `composer.insert_body_at_marker_compose()` — docxcompose 拼接正文
- `image_handler._insert_image_to_placeholder()` — 插入图表图片
- `post_processor._apply_font_constraints()` — 统一字体
- `post_processor._verify_appendix_with_lxml()` — 验证法律附录
