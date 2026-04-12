# P2 Schema 调整：文件版本 + 状态权限

> 调整日期：2026-04-12
> 前置：P1（作者字段合并 + 状态日志元数据）已完成
> 范围：文件版本存储、report_version 表处理、状态权限矩阵

---

## 变更 3：文件存储路径重构

### 设计决策

- 按文档类型分目录：`report/` 和 `model/`
- 时间戳目录区分版本，格式 `YYYYMMDD_HHmmss`
- 历史文件保留在 storage，不建 log 表

### 路径结构

```
reports/{report_id}/report/20260412_143500/file.docx
reports/{report_id}/report/20260412_143500/file.pdf
reports/{report_id}/model/20260412_143500/file.xlsx
```

---

## 变更 4：删除 `report_version` 表

### 设计决策

- 不需要单独的文件历史表，当前文件路径存 `report` 表即可
- 历史文件通过 storage 的 timestamp 目录保留，需要时按目录名排序取
- `snapshot_json`（elements/abstract/body）随表一起删除，内容在文件里，需要时从文件解析

### `report` 表新增字段

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `word_path` | `text` | nullable | 当前 Word 文件路径 |
| `pdf_path` | `text` | nullable | 当前 PDF 文件路径 |
| `model_path` | `text` | nullable | 当前 Model 文件路径 |

### `report` 表删除字段

| 字段 | 说明 |
|------|------|
| `current_version_no` | 版本号概念随 `report_version` 一起移除 |

### 删除内容

- `report_version` 表（含约束、索引）
- 所有引用 `report_version` 的函数逻辑

### 受影响的 RPC

| 函数 | 变更 |
|------|------|
| `commit_draft_version` | 删除或重写，不再插入 version 记录 |
| `submit_report` | 不再引用 `current_version_no` |

---

## 变更 5：状态与权限矩阵

### 状态机（不变）

```
draft → submitted → published
                  → rejected → draft
                             → submitted
```

### 权限矩阵

| 操作 | draft | submitted | published | rejected |
|------|-------|-----------|-----------|----------|
| 修改报告信息 | ✅ | ❌ | ❌ | ✅ |
| 上传文件 | ✅ | ❌ | ❌ | ✅ |
| 提交 | ✅ | ❌ | ❌ | ✅ |
| 发布 | ❌ | ✅(admin) | ❌ | ❌ |
| 退回 | ❌ | ✅(admin) | ❌ | ❌ |

### 设计决策

- rejected 保持 rejected 状态，不自动变 draft
- rejected 权限和 draft 一致（可修改信息、上传文件、提交）
- model 文件和 report 文件权限一致
