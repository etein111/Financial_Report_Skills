# renderer.py Document 重载优化设计

## 问题

`render_report()` 中 `Document` 对象被重复加载 7+ 次：

| 步骤 | 操作 | 问题 |
|------|------|------|
| 9 | `doc = Document(str(temp_path))` → save | 加载 1 |
| 11 | `doc = Document(output_path)` | reload |
| 12 | `doc = Document(output_path)` | reload |
| 13 | `doc = Document(output_path)` | reload |
| 最终验证 | `final_doc = Document(output_path)` | reload |

每次 `Document(path)` 都从 ZIP 读取解压，每次 `doc.save()` 都压缩写回。

---

## 方案

**原则：单一加载点，一次性保存。**

`composer.save(output_path)` 后，加载一次 `Document`，后续所有修改在内存中进行，只在最后保存两次（`_restore_jinja_in_charts` 和 `_apply_font_constraints` 之后各一次）。

---

## 新流程

```
1.  chart 生成（并行，已完成）
2.  docxtpl render → temp_path
3.  abstract 插入 → doc.save(temp_path)        # 写入 temp_path
4.  composer 合并 → output_path                # 写入 output_path
5.  doc = Document(output_path)                 # 唯一一次加载
6.  english_summary 插入 → doc.save(output_path)
7.  _apply_english_summary_margins(doc)         # 直接修改 doc.element
8.  relative_chart 插入 → doc.save(output_path)
9.  recommendation_chart 插入 → doc.save(output_path)
10. doc = Document(output_path)                  # 为 _restore_jinja 重新加载（必须）
11. _restore_jinja_in_charts(output_path, ...)  # 写文件（操作 XML bytes）
12. _apply_font_constraints(output_path, ...)     # 写文件
13. 验证（读取文件）
```

**关键变化：**
- 步骤 5 之后，步骤 6-9 共用同一个 `doc` 对象，4 次 save 变为可优化
- 步骤 10 是因为 `_restore_jinja_in_charts` 需要操作 ZIP 级别的字节流，必须写文件后才能读回

---

## 实现细节

### 1. `content_inserter.py` — `_apply_english_summary_margins` 改造

**现状：** 用 `common.read_docx_zip` 读 ZIP → etree 修改 → `common.write_docx_zip` 写回

**改造后：** 接收 `Document` 对象，直接修改 `doc.element.body`

```python
def _apply_english_summary_margins(
    docx_path: str,
    margins: Dict[str, str],
) -> bool:
    # 兼容旧签名（str path）
    doc = Document(docx_path)
    return _apply_english_summary_margins_doc(doc, margins)

def _apply_english_summary_margins_doc(
    doc: Document,
    margins: Dict[str, str],
) -> bool:
    # 直接操作 doc.element.body
    ...
```

调用方从 `renderer.py` 传入 `doc` 对象，不再重新加载。

### 2. `renderer.py` — 合并步骤 6-9 的 save 次数

**现状：** 每次 chart/english_summary 插入后立即 `doc.save()`

**优化后：** 在步骤 9 完成后统一 `doc.save(output_path)` 一次

但由于步骤 10 之后还需要 `_restore_jinja_in_charts` 写文件，步骤 9 的 save 是必要的（作为步骤 10 的前置条件）。

**结论：** save 次数从 7+ 减少到 **3 次**（步骤 3、步骤 9、步骤 12）。

### 3. `composer.py` — 暂不改动返回值

`insert_body_at_marker_compose` 内部使用 `docxcompose`，必须写文件后才能让外部复用。保持原样。

---

## 文件修改清单

| 文件 | 修改内容 |
|------|----------|
| `content_inserter.py` | 新增 `_apply_english_summary_margins_doc(doc, margins)`，原函数改为 facade |
| `renderer.py` | 重构步骤 5-13，合并 save，移除重复 `Document` 加载 |
| `post_processor.py` | 无需修改（已直接操作 ZIP bytes） |

---

## 预期效果

- `Document` 加载次数：7+ → **2 次**（步骤 5、步骤 10）
- `doc.save()` 调用次数：7+ → **3 次**（步骤 3、步骤 9、步骤 12）
- 文件 I/O 读写：大幅减少
