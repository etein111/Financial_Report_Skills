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

冗余说明：`lead_analyst_email` 与 `analyst_emails[1]`（PostgreSQL 数组 1-indexed）存在冗余。保留冗余是为了索引便利和直接查询效率，一致性由 RPC 写入时保证。

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
- **触发器统一快照**：每次状态流转都自动记录，覆盖所有路径
- **AFTER UPDATE 触发器**：与现有 BEFORE UPDATE 校验触发器职责分离

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

### 新增触发器

- 新增 AFTER UPDATE 触发器，在 report.status 变化时自动 INSERT `report_status_log` + 构造 `metadata`
- 现有 BEFORE UPDATE 触发器（`report_enforce_status_transition`）保持不变，仅做校验

### 受影响的 RPC

| 函数 | 变更 |
|------|------|
| `submit_report` | 移除手动 INSERT `report_status_log`，改由触发器统一写入 |

---

## 完整受影响清单

### 新增

- `report.lead_analyst_email` 字段
- `report.analyst_emails` 字段
- `report_status_log.metadata` 字段
- AFTER UPDATE 触发器（统一写 status_log + metadata）

### 修改

- `init_draft_report` RPC：直接写 report 的 analyst 字段
- `submit_report` RPC：移除手动 INSERT status_log，改由触发器写入
- `validators.py`：查询 `report.analyst_emails` 替代 `report_analyst`

### 删除

- `report_analyst` 表（含索引、约束、触发器、RLS 策略）
- `init_draft_report` 中对 `report_analyst` 的 DELETE+INSERT 逻辑
