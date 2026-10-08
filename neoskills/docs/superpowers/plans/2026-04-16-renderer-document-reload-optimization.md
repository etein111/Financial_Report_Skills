# renderer.py Document 重载优化实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `render_report()` 中的 Document 加载从 7+ 次减少到 2 次，doc.save() 从 7+ 次减少到 3 次。

**Architecture:** 在 `composer.save(output_path)` 后一次性加载 Document，后续所有修改在内存中进行。`_apply_english_summary_margins` 改造为直接操作 `doc.element.body`。chart 插入和 english_summary 插入后统一 save 一次。

**Tech Stack:** python-docx, docxcompose, lxml

---

## 文件修改概览

| 文件 | 职责 |
|------|------|
| `content_inserter.py` | 新增 `_apply_english_summary_margins_doc(doc, margins)`，原函数改为 facade |
| `renderer.py` | 重构步骤 5-13，合并 save，移除重复 Document 加载 |

---

## Task 1: content_inserter.py — 改造 `_apply_english_summary_margins`

**Files:**
- Modify: `skills/report_maker/scripts/content_inserter.py:143-216`

- [ ] **Step 1: 读取当前 `_apply_english_summary_margins` 完整代码**

确认函数边界：line 143 到 216。理解其使用 `etree.fromstring(files['word/document.xml'])` 而非 `doc.element.body` 的原因。

- [ ] **Step 2: 新增 `_apply_english_summary_margins_doc(doc, margins)` 函数**

在 `content_inserter.py` 中新增函数，接收 `Document` 对象和 `margins` 字典，直接修改 `doc.element.body`：

```python
def _apply_english_summary_margins_doc(doc: Document, margins: Dict[str, str]) -> bool:
    """应用英文摘要部分的页边距（直接操作 Document 对象）。

    Args:
        doc: Document 对象
        margins: 页边距字典

    Returns:
        是否成功
    """
    if not margins:
        return False

    W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    body = doc.element.body
    all_elements = list(body)

    es_start_idx = None
    for idx, elem in enumerate(all_elements):
        if elem.tag == f'{{{W_NS}}}p':
            text = common.get_element_text(elem).strip()
            if text == _ENGLISH_SUMMARY_START_MARKER:
                es_start_idx = idx
                break

    if es_start_idx is None or es_start_idx == 0:
        return False

    # 在 es_start_idx 之前找最近的 sectPr
    for i in range(es_start_idx - 1, -1, -1):
        elem = all_elements[i]
        if elem.tag == f'{{{W_NS}}}p':
            pPr = elem.find(f'{{{W_NS}}}pPr')
            if pPr is not None:
                sectPr = pPr.find(f'{{{W_NS}}}sectPr')
                if sectPr is not None:
                    pgMar = sectPr.find(f'{{{W_NS}}}pgMar')
                    if pgMar is None:
                        pgMar = etree.SubElement(sectPr, f'{{{W_NS}}}pgMar')

                    for attr, val in margins.items():
                        pgMar.set(f'{{{W_NS}}}{attr}', val)

                    print(f"  已应用 english_summary 页边距")
                    return True

    return False
```

注意：需要从 `lxml import etree`，如果尚未导入则添加。

- [ ] **Step 3: 改造原 `_apply_english_summary_margins(path, margins)` 为 facade**

将原函数改为调用新函数，保持向后兼容：

```python
def _apply_english_summary_margins(
    docx_path: str,
    margins: Dict[str, str],
) -> bool:
    """应用英文摘要部分的页边距（文件路径版本，兼容旧调用方）。

    Args:
        docx_path: 文档路径
        margins: 页边距字典

    Returns:
        是否成功
    """
    if not DOCX_AVAILABLE:
        return False
    if not margins:
        return False
    try:
        doc = Document(docx_path)
        return _apply_english_summary_margins_doc(doc, margins)
    except Exception as e:
        print(f"  应用 english_summary 页边距失败: {e}")
        return False
```

- [ ] **Step 4: 验证语法**

Run: `python -m py_compile skills/report_maker/scripts/content_inserter.py`
Expected: 无输出（成功）

- [ ] **Step 5: 提交**

```bash
git add skills/report_maker/scripts/content_inserter.py
git commit -m "refactor(content_inserter): extract _apply_english_summary_margins_doc for in-memory operation"
```

---

## Task 2: renderer.py — 重构 Document 加载和 save 逻辑

**Files:**
- Modify: `skills/report_maker/scripts/renderer.py:183-327`

- [ ] **Step 1: 读取当前 renderer.py 相关代码段**

重点关注步骤 9（abstract 插入）到步骤 13（验证），确认当前 save 位置。

- [ ] **Step 2: 确认 composer 后的首次 Document 加载位置**

在 `insert_body_at_marker_compose` 成功后（line ~225），添加：
```python
# 步骤 5: 加载 Document，后续所有操作复用此对象
doc = Document(output_path)
```

- [ ] **Step 3: 重构步骤 11（english_summary 插入）**

当前代码：
```python
if english_summary_path and ...:
    doc = Document(output_path)   # ← 删除这行
    english_summary_doc = Document(english_summary_path)
    ...
    doc.save(output_path)         # ← 保留
```

改造后：移除 `doc = Document(output_path)`，直接用已有的 `doc` 对象。

- [ ] **Step 4: 合并步骤 8.5 和 8.6 的 save**

当前每次 chart 插入后都 `doc.save()`。改造后：
```python
# 步骤 8.5 插入 relative_chart
if relative_chart_generated:
    relative_chart_path = Path(output_path).parent / "relative_chart.png"
    if relative_chart_path.exists():
        chart_inserted = _insert_image_to_placeholder(
            doc, RELATIVE_CHART_MARKER, str(relative_chart_path), width_cm=6.35
        )
        if chart_inserted:
            print(f"  ✅ relative_chart 已插入到文档")

# 步骤 8.6 插入 recommendation_chart
if recommendation_chart_generated:
    recommendation_chart_path = Path(output_path).parent / "recommendation_chart.png"
    if recommendation_chart_path.exists():
        chart_inserted = _insert_image_to_placeholder(
            doc, RECOMMENDATION_CHART_MARKER, str(recommendation_chart_path), width_cm=18
        )
        if chart_inserted:
            print(f"  ✅ recommendation_chart 已插入到文档")

# 统一保存（步骤 9）
doc.save(output_path)
print(f"  已保存文档（含 english_summary 和 charts）")
```

- [ ] **Step 5: 修改 `_apply_english_summary_margins` 调用**

将：
```python
if es_margins and es_inserted:
    _apply_english_summary_margins(output_path, es_margins)
```
改为：
```python
if es_margins and es_inserted:
    _apply_english_summary_margins_doc(doc, es_margins)
```

并确保 `content_inserter` 中的 `_apply_english_summary_margins_doc` 已正确导入。

- [ ] **Step 6: 验证最终 doc.save() 次数**

确认 save 点：
1. 步骤 3：`doc.save(str(temp_path))` — abstract 后
2. 步骤 9：`doc.save(output_path)` — english_summary + charts 后
3. 步骤 12：`_apply_font_constraints` 内部 write（不可避免）

- [ ] **Step 7: 验证语法**

Run: `python -m py_compile skills/report_maker/scripts/renderer.py`
Expected: 无输出（成功）

- [ ] **Step 8: 提交**

```bash
git add skills/report_maker/scripts/renderer.py
git commit -m "refactor(renderer): reduce Document reload from 7+ to 2, save from 7+ to 3"
```

---

## Task 3: 集成测试

**Files:**
- Test: `skills/report_maker/tests/integration/test_report_workflow.py`

- [ ] **Step 1: 运行现有测试确认基础功能未被破坏**

Run: `cd skills/report_maker && python -m pytest tests/ -v --tb=short 2>&1 | head -80`
Expected: 测试通过（无 regression）

- [ ] **Step 2: 如果有集成测试，确认 Document 加载次数逻辑正确**

检查 `test_report_workflow.py` 中是否有验证 save 次数的测试，如有则验证通过。

---

## 验证清单

- [ ] `Document(path)` 调用次数：7+ → 2（composer 后一次，restore_jinja 前一次）
- [ ] `doc.save()` 调用次数：7+ → 3（abstract 后、charts 后、font_constraints 后）
- [ ] `_apply_english_summary_margins` 仍可独立调用（path 重载）
- [ ] `_apply_english_summary_margins_doc` 可接收 Document 对象直接操作
- [ ] 所有测试通过
