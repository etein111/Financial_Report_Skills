# 01 提示词内嵌代码封装为函数

## 原则

SKILL.md 中的代码块，在对应模块里提取为可调用的函数。SKILL.md 暂不修改，代码块保留作为参考。LLM 可选择调用函数或按提示词中的代码执行。

---

## 实例 1：预处理（SKILL.md 1.5 节，第 200-228 行）— 已完成

**问题**：29 行过程式代码直接写在提示词里，不可测试。

**方法**：封装为 `docx_reader.preprocess_for_extraction(docx_path)`。

**变更**：`docx_reader.py` 新增 `preprocess_for_extraction()`。

### 如果未来替换 SKILL.md 中的代码块

将第 200-228 行的代码块替换为：

> 执行 `docx_reader.preprocess_for_extraction(draft_path)`，将输出打印到对话上下文。
>
> 输出分为三段：
> 1. `=== 表格内容 ===` — 所有表格的扁平化文本
> 2. `=== 段落内容（带索引）===` — 每段以 `[P{idx}/{total}]` 格式标注位置
> 3. `=== 最后 50 个段落 ===` — 英文摘要标题通常在此范围内
>
> 不要创建临时脚本文件，直接在 REPL 中执行。

---

## 实例 2：渲染调用（SKILL.md 2.3 节，第 476-498 行）— 待实施

**问题**：22 行代码重复固定调用模式：`load_yaml` → 构造路径 → `render_report()`。

**方法**：封装为 `renderer.render_from_dir(report_dir, report_type, language)`。

**变更**：`renderer.py` 新增 `render_from_dir()`。

### 如果未来替换 SKILL.md 中的代码块

将第 476-498 行的代码块替换为：

> 执行 `renderer.render_from_dir(report_dir, report_type, language)` 渲染最终报告。
>
> - `report_dir`：报告目录路径（如 `reports/cirrus(2507)_20251021`）
> - `report_type`：报告类型，决定模板选择（如 `"company"`）
> - `language`：`"zh"` 或 `"en"`，英文报告跳过 english_summary
>
> 目录下必须存在 `elements.yaml`；`abstract.docx` 和 `body.docx` 至少有一个。
> `english_summary.docx` 可选，缺失时不插入英文摘要。
>
> 输出文件路径由 `common.get_report_output_path()` 决定。

---

## 实例 3：占位符验证（SKILL.md 2.4 节，第 518-536 行）— 待实施

**问题**：`verify_no_placeholders()` 已经是完整的函数定义，但写在提示词里。

**方法**：搬到 `post_processor.py`，逻辑不变。

**变更**：`post_processor.py` 新增 `verify_no_placeholders()`。

### 如果未来替换 SKILL.md 中的代码块

将第 518-536 行的代码块替换为：

> 执行 `post_processor.verify_no_placeholders(output_path)`，检查渲染后的报告中是否存在未填充的 `{{}}` 占位符。
>
> - 返回 `True` 表示验证通过
> - 抛出 `ValueError` 表示发现残留占位符，错误消息中列出前 5 个
>
> 如果验证失败，排查 `elements.yaml` 中是否缺少对应字段。
