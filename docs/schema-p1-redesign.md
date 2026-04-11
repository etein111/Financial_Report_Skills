# P1 Schema 调整：作者字段合并 + 状态日志元数据

> 调整日期：2026-04-12
> 范围：仅 P1，不涉及文件版本（P2 另文档）

---

## 变更 1：删除 `report_analyst` 表，作者信息移入 `report`

### 设计决策

- `report_analyst` 本质是 report 的列表属性，不存在独立查询需求
- 查"某分析师的所有报告"走 `coverage_analyst` 更合理
- 合并后简化存储过程（`init_draft_report` 不再需要批量替换关联行）

### `report` 表新增字段

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `lead_analyst_email` | `text` | `NOT NULL` | 第一作者/团队负责人，代表 team |
| `analyst_emails` | `text[]` | `NOT NULL` | 所有署名分析师，`[0]` 即 lead |

命名规则：统一使用 `analyst` 前缀，保持一致。

### 删除内容

- `report_analyst` 表（含约束、索引、触发器、RLS 策略）
- 所有引用 `report_analyst` 的函数逻辑

### 受影响的 RPC

| 函数 | 变更 |
|------|------|
| `init_draft_report` | 原 bulk-replace `report_analyst` → 直接写 `report.lead_analyst_email` + `report.analyst_emails` |

---

## 变更 2：`report_status_log` 新增 `metadata` 字段

### 设计决策

- 状态流转时快照 report 业务字段，用于审计和回溯
- 不放 `status`（已有 `from_status`/`to_status`）
- 不放运营字段（`owner_user_id`、`published_by`、`published_at`）
- 文件路径现在就加（P2 文件版本调整时 metadata 结构不变）

### `report_status_log` 表新增字段

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `metadata` | `jsonb` | `NOT NULL DEFAULT '{}'` | 状态流转时的报告快照 |

### metadata 快照字段清单

```json
{
  "title": "text",
  "report_type": "text",
  "lead_analyst_email": "text",
  "analyst_emails": ["text"],
  "coverage_id": "uuid | null",
  "ticker": "text | null",
  "sector_id": "uuid | null",
  "region_code": "text | null",
  "rating": "text | null",
  "target_price": "numeric | null",
  "investment_thesis": "text | null",
  "report_language": "text | null",
  "contact_person": "text | null",
  "word_path": "text | null",
  "pdf_path": "text | null",
  "model_path": "text | null"
}
```

### 受影响的 RPC

| 函数 | 变更 |
|------|------|
| `submit_report` | INSERT `report_status_log` 时构造并写入 `metadata` |
