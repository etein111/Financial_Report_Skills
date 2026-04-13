# P1 Schema 调整 Spec：作者字段合并 + 状态日志元数据

> 日期：2026-04-13
> 范围：仅 P1，不涉及文件版本（P2 另文档）

---

## 背景

当前 `report_analyst` 是一张独立的关联表，存储报告的署名分析师列表。经评估，此表的查询需求完全可以被 `report` 表的字段覆盖，且现有存储过程因此引入额外复杂度。

当前 `report_status_log` 缺少业务快照字段，审计时无法回溯流转时刻的报告状态。日志写入分散在各 RPC 中，存在遗漏路径的风险。

---

## 变更 1：删除 `report_analyst` 表，作者信息移入 `report`

### 变更目标

- 消除 `report_analyst` 表，将署名分析师列表内联到 `report` 表
- 简化 `init_draft_report` RPC（去掉 DELETE + INSERT 循环）
- `validate_report` 改为从 `report` 字段读取，不再 JOIN 额外表

### `report` 表新增字段

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `lead_analyst_email` | `text` | `NOT NULL` | 第一作者，`analyst_emails[1]` 的冗余，便于直接索引 |
| `analyst_emails` | `text[]` | `NOT NULL` | 全部署名分析师邮箱，按 `author_order` 排序（PostgreSQL 数组 1-indexed，`[1]` 即 lead） |

冗余说明：`lead_analyst_email` 与 `analyst_emails[1]` 存在冗余，一致性由 `init_draft_report` RPC 写入时保证。

### `init_draft_report` RPC 改动

原逻辑：INSERT/UPDATE `report` 主字段 → DELETE + INSERT `report_analyst` 循环

新逻辑：在 INSERT/UPDATE `report` 时，直接写 `lead_analyst_email` 和 `analyst_emails`。
- 从 `p_draft->'analysts'` 按 `author_order` 升序排序后取第一个元素的 `analyst_email` 作为 `lead_analyst_email`
- 将完整列表转换为 `text[]` 写入 `analyst_emails`
- 删除 `DELETE FROM report_analyst` 和后续 INSERT 循环

### `validate_report` RPC 改动

原逻辑：`SELECT count(*) FROM report_analyst WHERE report_id = p_report_id`

新逻辑：
- 分析师非空校验：`CARDINALITY(v_report.analyst_emails) = 0`
- contact_person 在列表中：`v_report.contact_person = ANY(v_report.analyst_emails)`（大小写不敏感，用 `lower()` 处理）
- 分析师有效性校验：遍历 `v_report.analyst_emails` 数组，LEFT JOIN `analyst` 表，收集不存在或已停用的邮箱

### 删除内容

- `report_analyst` 表（含唯一约束、索引 `report_analyst_uniq_order`、ON DELETE CASCADE 外键）
- RLS policy：`ra_select`、`ra_insert`、`ra_delete`
- 触发器：`trg_report_analyst_updated_at`
- `init_draft_report` 中对 `report_analyst` 的 DELETE + INSERT 逻辑

### Python 层改动

- `test_draft_report.py`：`test_report_analyst_records_exist` 改为查 `report.lead_analyst_email` 和 `report.analyst_emails`，断言新字段值正确

---

## 变更 2：`report` 表新增 `rejection_reason`，`report_status_log` 新增 `metadata`，触发器统一写日志

### 变更目标

- `rejection_reason` 作为永久字段存储在 `report` 表，避免临时变量方案的复杂度
- 触发器统一接管所有状态变更的日志写入，消除 RPC 手动 INSERT 分散的风险
- `metadata` 字段在每次流转时快照 report 的业务状态，用于审计和回溯

### `report` 表新增字段

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `rejection_reason` | `text` | — | 退回原因，仅 `submitted → rejected` 时由 reject RPC 写入，其余情况为 NULL |

### `report_status_log` 表新增字段

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `metadata` | `jsonb` | `NOT NULL DEFAULT '{}'` | 状态流转时的报告业务字段快照 |

### metadata 快照结构

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

文件路径（`word_path`、`pdf_path`、`model_path`）从 `report_version` 表按 `version_no = NEW.current_version_no` 读取。若对应版本行不存在，三个路径均为 null，不报错。

### 新增 AFTER UPDATE 触发器

**触发条件：** `NEW.status IS DISTINCT FROM OLD.status`

**触发器函数逻辑：**

```
1. 读取 report_version（version_no = NEW.current_version_no）获取文件路径
2. 构建 metadata jsonb
3. INSERT report_status_log：
   - report_id      = NEW.id
   - from_status    = OLD.status
   - to_status      = NEW.status
   - action_by      = auth.uid()
   - action_by_name = auth.jwt()->>'email'
   - version_no     = NEW.current_version_no
   - reason         = NEW.rejection_reason（to_status = 'rejected' 时有值，其余 NULL）
   - metadata       = 构建好的 jsonb
```

**职责分离：**
- 现有 `trg_report_status_transition`（BEFORE UPDATE）：仅做状态流转合法性校验，不变
- 新增触发器（AFTER UPDATE）：仅写日志，不做校验

**不声明 SECURITY DEFINER**，以调用者身份执行，依赖现有 `rsl_insert` RLS policy。

### RPC 改动

| 函数 | 改动 |
|------|------|
| `submit_report` | 删除手动 INSERT `report_status_log`（触发器接管） |
| `retract_report` | 删除手动 INSERT `report_status_log`（触发器接管） |
| 将来 publish/reject RPC | 无需手动写日志；reject RPC 需额外写 `report.rejection_reason` |

### Python 层改动

- `test_submit_report.py`：`test_status_log_created` 补充 `metadata` 非空断言（`assert log["metadata"]` 或检查具体字段）
- `test_retract_report.py`：`test_retract_submitted_report` 补充 `metadata` 非空断言

---

## 完整变更清单

### 新增（数据库）

- `report.lead_analyst_email text NOT NULL`
- `report.analyst_emails text[] NOT NULL`
- `report.rejection_reason text`
- `report_status_log.metadata jsonb NOT NULL DEFAULT '{}'`
- AFTER UPDATE 触发器函数及触发器（写 status_log + metadata）

### 修改（数据库）

- `init_draft_report`：直接写 `lead_analyst_email` / `analyst_emails`，删除 report_analyst 操作
- `validate_report`：从 `report.analyst_emails` 读取，不再查 `report_analyst`
- `submit_report`：删除手动 INSERT `report_status_log`
- `retract_report`：删除手动 INSERT `report_status_log`

### 删除（数据库）

- `report_analyst` 表（含索引、约束、外键、RLS policy、触发器）

### 修改（Python）

- `test_draft_report.py`：`test_report_analyst_records_exist` 改为验证 `report.analyst_emails`
- `test_submit_report.py`：补充 `metadata` 断言
- `test_retract_report.py`：补充 `metadata` 断言

---

## 迁移文件规划

每个迁移文件独立、可回滚：

1. **`xxx_115_report_analyst_fields.sql`**
   - `report` 表新增 `lead_analyst_email`、`analyst_emails`、`rejection_reason` 字段
   - 更新 `init_draft_report` RPC
   - 更新 `validate_report` RPC

2. **`xxx_116_drop_report_analyst.sql`**
   - 删除 `report_analyst` 表（含依赖的 policy、触发器、索引）
   - 依赖 115 先执行

3. **`xxx_117_status_log_metadata.sql`**
   - `report_status_log` 新增 `metadata` 字段
   - 新增 AFTER UPDATE 触发器函数及触发器
   - 更新 `submit_report` RPC（删除手动 INSERT）
   - 更新 `retract_report` RPC（删除手动 INSERT）

迁移顺序：115 → 116 → 117，互不依赖可单独回滚。
