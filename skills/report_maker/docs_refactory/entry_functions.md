# report_maker 入口函数表

基于 `cirrus(2507)_20251021` 样本报告的完整流程记录。

## 类型说明

| 类型 | 含义 |
|------|------|
| 🐍 Python | 可调用的 Python 函数，存在于代码库中 |
| 🤖 LLM | LLM 自身完成的操作，无对应 Python 函数 |
| ⌨️ CLI | 外部命令行工具 |

## 已验证的入口函数（Python）

| 步骤 | 入口函数 | 模块 | 文件:行号 | 模拟结果 |
|------|---------|------|----------|---------|
| 1.4 加载模板 | `resolve_template_for_report()` | `neolyst_integration` | neolyst_integration.py:35 | — |
| 1.5 预处理 | `preprocess_for_extraction()` | `docx_reader` | docx_reader.py:234 | 547 行输出 ✅ |
| 1.8 提取摘要 | `extract_abstract()` | `splitter` | splitter.py:267 | 39KB ✅ |
| 1.8 提取正文 | `extract_body()` | `splitter` | splitter.py:753 | 1.6MB ✅ |
| 1.8 提取英文摘要 | `extract_english_summary()` | `splitter` | splitter.py:1432 | — |
| 1.10 保存字段 | `save_yaml()` | `common` | common.py:187 | 54 字段 ✅ |
| 1.11 保存草稿 | `save_report()` | `skills.neolyst.scripts.report` | 外部模块 | — |
| 4b 准备草稿 | `prepare_and_save_draft()` | `workflow` | workflow.py:38 | — |
| 4b 提交报告 | `submit_report_workflow()` | `workflow` | workflow.py:132 | — |
| 4b 解析 coverage | `resolve_coverage()` | `neolyst_integration` | neolyst_integration.py:109 | — |
| 2.3 渲染 | `render_report()` | `renderer` | renderer.py:86 | 1.6MB, 256段落, 41表格, 29图片 ✅ |
| 2.5 转 PDF | `word2pdf convert`（CLI） | — | — | — |

## LLM 操作（非 Python 函数）

| 步骤 | SKILL.md 位置 | 行为 |
|------|-------------|------|
| 1.6 提取 elements | 第 236-282 行 | 读取预处理输出 + schema.yaml，一次性返回所有字段和位置标记 |
| 1.7 确认提取结果 | 第 284-308 行 | 展示提取结果表格，等待用户确认或修正 |
| 1.9 确认字段 | 第 349-362 行 | 展示所有字段表格，等待用户确认 |

## 计划中但未实施的函数

| 步骤 | 计划函数 | 目标模块 | 状态 |
|------|---------|---------|------|
| 2.3 渲染（封装） | `render_from_dir()` | `renderer` | 待实施，见 01-extract-preprocess-function.md 实例 2 |
| 2.4 验证 | `verify_no_placeholders()` | `post_processor` | 待实施，见 01-extract-preprocess-function.md 实例 3 |

> 目前 2.3 步骤直接调用 `render_report()`，2.4 步骤由 LLM 按提示词中的代码块执行。

## 数据流

```
preprocess_for_extraction()  →  print 到对话上下文
                                       ↓
                              LLM 读取 + schema.yaml → 返回字段和标记
                                       ↓
extract_abstract()          ←  abstract_scope / markers
extract_body()              ←  body_start_marker / body_end_marker
extract_english_summary()   ←  english_summary markers
        ↓
save_yaml()  →  elements.yaml
        ↓
render_report()  →  最终报告 .docx
        ↓
LLM 执行占位符验证（按提示词代码块）→  确认无 {{}} 残留
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
