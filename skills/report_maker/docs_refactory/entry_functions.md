# report_maker 入口函数表

基于 `cirrus(2507)_20251021` 样本报告的完整流程记录。

## 调用顺序

| 步骤 | 文件 | 入口函数 | 模块 | 输出大小 |
|------|------|---------|------|---------|
| 1.5 预处理 | `01_preprocess.txt` | `preprocess_for_extraction()` | `docx_reader` | 88KB (547行) |
| 1.7 提取摘要 | `02_abstract.docx` | `extract_abstract()` | `splitter` | 39KB |
| 1.8 提取正文 | `03_body.docx` | `extract_body()` | `splitter` | 1.6MB |
| 1.10 保存字段 | `04_elements.yaml` | `save_yaml()` | `common` | 1KB |
| 2.3 渲染报告 | `05_rendered_report.docx` | `render_report()` | `renderer` | 1.6MB |
| 2.4 验证 | `06_verify.txt` | 占位符验证 | `docx.Document` + regex | 64B |

## 数据流

```
preprocess_for_extraction()  →  print 到对话上下文  →  LLM 提取字段和标记
                                                           ↓
extract_abstract()  ←  start_marker / end_marker
extract_body()      ←  start_marker / end_marker
        ↓
save_yaml()  →  elements.yaml
        ↓
render_report()  →  最终报告 .docx
        ↓
占位符验证  →  确认无 {{}} 残留
```

## render_report() 内部调用链

- `chart_generator.generate_relative_chart()` — 相对收益对比图
- `chart_generator.generate_recommendation_chart()` — 推荐走势图
- `content_inserter.insert_abstract_to_cell()` — 插入摘要到表格
- `composer.insert_body_at_marker_compose()` — docxcompose 拼接正文
- `image_handler.insert_image_to_placeholder()` — 插入图表图片
- `post_processor.apply_font_constraints()` — 统一字体
- `post_processor.verify_appendix_with_lxml()` — 验证法律附录
