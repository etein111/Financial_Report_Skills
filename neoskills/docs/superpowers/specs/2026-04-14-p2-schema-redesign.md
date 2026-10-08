# P2 Schema 设计：文件版本路径 + 删除 report_version

> 日期：2026-04-14
> 前置：P1（作者字段合并 + 状态日志元数据）已完成
> 范围：删除 report_version 表、文件存储路径重构、RPC 拆分重组

---

## 1 Schema 变更

### 1.1 report 表新增字段

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `word_path` | `text` | nullable | 当前 Word 文件存储路径 |
| `pdf_path` | `text` | nullable | 当前 PDF 文件存储路径 |
| `model_path` | `text` | nullable | 当前 Model 文件存储路径 |

新建报告时三个字段均为 NULL，上传后写入。

### 1.2 report 表删除字段

| 字段 | 说明 |
|------|------|
| `current_version_no` | 版本号概念随 report_version 一起移除 |

CHECK 约束 `current_version_no >= 0` 随列删除自动移除。

### 1.3 删除 report_version 表

连带删除：
- UNIQUE 约束 `(report_id, version_no)`
- 索引 `idx_report_version_report_version_desc`
- 外键约束 `report_version_report_id_fkey`
- RLS 策略（SELECT / INSERT）

### 1.4 report_status_log 表

删除 `version_no` 列。trigger 不再写入该字段。

---

## 2 存储路径规则

### 2.1 路径格式

```
reports/{report_id}/report/{YYYYMMDD_HHmmss}/{filename}
reports/{report_id}/model/{YYYYMMDD_HHmmss}/{filename}
```

- `file_category` 取值：`'report'`（Word + PDF 共用目录）、`'model'`
- 时间戳由 `generate_upload_path` RPC 在 SQL 侧用 `to_char(now(), 'YYYYMMDD_HH24MISS')` 生成
- 同一次 `upload_report_files` 调用中 Word 和 PDF 共享同一个时间戳目录
- 历史文件保留在 Storage 旧目录中，不删除

### 2.2 generate_upload_path RPC

```sql
generate_upload_path(p_report_id uuid, p_file_category text)
  RETURNS text
```

- 纯计算，不写 DB
- 校验 `p_file_category IN ('report', 'model')`，否则 RAISE
- 校验 report 存在且 status IN ('draft', 'rejected')，否则 RAISE
- 返回路径前缀：`reports/{report_id}/{category}/{timestamp}/`
- 客户端拿到前缀后拼接文件名上传

### 2.3 Storage RLS

现有 reports bucket 策略通过 `split_part(name, '/', 1)` 提取 report_id。P2 路径中 report_id 仍为第一段，**Storage RLS 不需要修改**。

---

## 3 RPC 变更

### 3.1 新建

| RPC | 签名 | 职责 |
|-----|------|------|
| `generate_upload_path` | `(p_report_id uuid, p_file_category text) → text` | 纯计算，返回路径前缀 |
| `update_report_doc_paths` | `(p_report_id uuid, p_word_path text, p_pdf_path text) → void` | 更新 word_path + pdf_path |
| `update_model_path` | `(p_report_id uuid, p_model_path text) → void` | 更新 model_path |

三个 RPC 共同约束：
- report 必须存在
- status 必须为 `'draft'` 或 `'rejected'`
- 调用者必须是 owner（RLS 保证）
- 参数必填，调用即更新

### 3.2 修改

| RPC | 变更 |
|-----|------|
| `upsert_report`（原 `init_draft_report`） | 改名；去掉 `next_version_no` 返回值；不再操作 `current_version_no`；返回 `TABLE(report_id uuid)` |
| `submit_report` | 去掉 version_no 校验和返回值；validate_report 检查 `report.word_path`/`pdf_path` 非空；返回 `TABLE(report_id uuid, status text)` |
| `retract_report` | 去掉 version_no 返回值；返回 `TABLE(report_id uuid, status text)` |
| `validate_report` | 去掉 `current_version_no > 0` 校验；去掉 report_version JOIN；改为检查 `report.word_path IS NOT NULL` 和 `report.pdf_path IS NOT NULL` |

### 3.3 删除

| RPC | 原因 |
|-----|------|
| `commit_draft_version` | 被 `update_report_doc_paths` + `update_model_path` 替代 |

### 3.4 Trigger 变更

`report_write_status_log()` trigger：
- 删除对 `report_version` 的 JOIN 查询
- 文件路径直接从 `NEW.word_path`、`NEW.pdf_path`、`NEW.model_path` 读取写入 metadata
- 不再写入 `version_no`（该列已删除）

---

## 4 Python 客户端变更

### 4.1 函数拆分

| 旧函数 | 新函数 | 文件 | 变更 |
|--------|--------|------|------|
| `save_draft_report()` | `save_report()` | `save_report.py`（原 `draft_report.py` 改名） | 只调 `upsert_report` RPC；返回 `{report_id}` |
| _(新建)_ | `upload_report_files()` | `upload_files.py` | generate_upload_path('report') → Storage upload Word+PDF → update_report_doc_paths |
| _(新建)_ | `upload_model_file()` | `upload_files.py` | generate_upload_path('model') → Storage upload Model → update_model_path |
| `submit_report()` | `submit_report()` | `submit_report.py` | 去掉 version_no 返回值 |
| `retract_report()` | `retract_report()` | `retract_report.py` | 去掉 version_no 返回值 |

### 4.2 返回值

```python
save_report()          → {"report_id": str}
upload_report_files()  → {"report_id": str, "word_path": str, "pdf_path": str}
upload_model_file()    → {"report_id": str, "model_path": str}
submit_report()        → {"report_id": str, "status": "submitted"}
retract_report()       → {"report_id": str, "status": "draft"}
```

### 4.3 客户端调用场景

**场景 1：新建报告（含文件）**
```
save_report()  →  upload_report_files()  →  upload_model_file()（可选）
```

**场景 2：修改信息（不换文件）**
```
save_report()
```

**场景 3：替换 Word + PDF**
```
upload_report_files()
```

**场景 4：只替换 Model**
```
upload_model_file()
```

**场景 5：修改信息 + 换文件**
```
save_report()  →  upload_report_files()
```

**场景 6：提交**
```
submit_report()
```

**场景 7：撤回 → 修改 → 重新提交**
```
retract_report()  →  save_report()（可选）  →  upload_report_files()（可选）  →  submit_report()
```

---

## 5 测试变更

### 5.1 测试文件

| 旧测试 | 新测试 | 变更 |
|--------|--------|------|
| `test_draft_report.py` | `test_save_report.py` | 重写；只测 upsert_report（新建/更新元数据）；去掉 version_no、report_version、Storage 断言 |
| _(新建)_ | `test_upload_files.py` | 测 upload_report_files + upload_model_file：路径格式、report 表字段更新、Storage 文件存在 |
| `test_submit_report.py` | `test_submit_report.py` | 去掉 version_no 断言；验证 word_path/pdf_path 非空才能提交 |
| `test_retract_report.py` | `test_retract_report.py` | 去掉 version_no 断言 |
| `test_validators.py` | `test_validators.py` | 去掉 current_version_no 和 report_version 用例；新增 word_path/pdf_path 为空校验 |
| `test_coverage.py` | `test_coverage.py` | fixture 去掉 current_version_no |

### 5.2 test_data.sql

- 7 条 `report` INSERT：去掉 `current_version_no`；新增 `word_path`、`pdf_path`、`model_path`（新路径格式）
- 删除全部 7 条 `report_version` INSERT
- 路径格式从 `reports/{id}/v{N}/file` 改为 `reports/{id}/report/{timestamp}/file`

### 5.3 关键断言

| 场景 | 断言 |
|------|------|
| save_report 新建 | report 存在，word_path/pdf_path/model_path 均为 NULL |
| save_report 更新 | 元数据变更，路径字段不变 |
| upload_report_files | word_path + pdf_path 更新为新时间戳路径；Storage 有文件 |
| upload_model_file | model_path 更新；word_path/pdf_path 不变 |
| 替换文件 | 路径为新时间戳；旧文件仍在 Storage |
| 提交校验 | word_path 或 pdf_path 为空时报错 |
| 状态流转 | status_log.metadata 含 word_path/pdf_path/model_path |

---

## 6 不在范围

- 状态权限矩阵（变更 5）：状态机和权限逻辑不变，仅去除 version_no 相关引用
- Storage 旧文件清理：历史文件保留，不主动删除
- 数据迁移：开发阶段无生产数据，直接删表重建
- Edge Function：当前不引入
