# P1 Schema 调整：两迭代拆分设计

> 日期：2026-04-14
> 前置 spec：[2026-04-13-p1-schema-redesign.md](./2026-04-13-p1-schema-redesign.md)
> 拆分原因：单次实施步骤过多（10 步），容易卡死；拆分后每个迭代 5-6 步，可独立验证

---

## 拆分策略

P1 schema 调整包含两个独立变更：

- **变更 1**：删除 `report_analyst` 表，作者信息移入 `report`
- **变更 2**：`report` 新增 `rejection_reason`，`report_status_log` 新增 `metadata`，触发器统一写日志

变更 2 的 metadata 快照包含 `lead_analyst_email` 和 `analyst_emails`，这两个字段由变更 1 新增。因此变更 1 是变更 2 的前置条件，反向无依赖。

拆分方式：**严格按变更边界拆**，每个迭代对应一个迁移文件，DDL、RPC、测试、文档聚焦一个主题。

---

## Iter A：分析师字段合并

> 迁移文件：`supabase migration new` 生成，逻辑编号 115

### DDL

1. `ALTER TABLE report ADD COLUMN lead_analyst_email text NOT NULL DEFAULT ''`
2. `ALTER TABLE report ADD COLUMN analyst_emails text[] NOT NULL DEFAULT '{}'`
3. 移除临时 DEFAULT：`ALTER TABLE report ALTER COLUMN lead_analyst_email DROP DEFAULT`、`ALTER COLUMN analyst_emails DROP DEFAULT`

### RPC：init_draft_report

从 `p_draft->'analysts'` 按 `author_order` 升序排序后：
- 取第一个元素的 `analyst_email` 写入 `lead_analyst_email`
- 将完整列表转为 `text[]` 写入 `analyst_emails`
- 删除 `DELETE FROM report_analyst` 和后续 INSERT 循环

### RPC：validate_report

- 分析师非空：`CARDINALITY(v_report.analyst_emails) = 0`
- contact_person 在列表中：`lower(v_report.contact_person) = ANY(SELECT lower(x) FROM unnest(v_report.analyst_emails) x)`
- 分析师有效性：遍历 `analyst_emails`，LEFT JOIN `analyst`，收集不存在或已停用的邮箱

### 删除

- `report_analyst` 的 RLS policy：`ra_select`、`ra_insert`、`ra_delete`
- 触发器 `trg_report_analyst_updated_at` 及其函数
- `report_analyst` 表（含唯一约束、索引、外键）

### Python

- `test_draft_report.py`：`test_report_analyst_records_exist` → 断言 `report.lead_analyst_email` 和 `report.analyst_emails`
- `test_draft_report.py`：teardown 注释去掉 `report_analysts`
- `draft_report.py`：模块注释更新

### 文档

- `references/interfaces.md`：`save_draft_report` 描述去掉 `report_analyst` 引用

### 验证标准

- `save_draft_report` 后 `report.lead_analyst_email` 和 `analyst_emails` 正确写入
- `validate_report` 检测：分析师为空、contact_person 不在列表、分析师停用
- `submit_report`（未改动）通过内部调用 `validate_report` 间接验证新字段

---

## Iter B：状态日志 metadata + 触发器

> 迁移文件：`supabase migration new` 生成，逻辑编号 116
> 前置条件：Iter A 已完成

### DDL

1. `ALTER TABLE report ADD COLUMN rejection_reason text`
2. `ALTER TABLE report_status_log ADD COLUMN metadata jsonb NOT NULL DEFAULT '{}'`

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

文件路径从 `report_version` 表按 `version_no = NEW.current_version_no` 读取。版本行不存在时三个路径均为 null。

### AFTER UPDATE 触发器

**条件：** `NEW.status IS DISTINCT FROM OLD.status`

**逻辑：**
1. 读取 `report_version`（`version_no = NEW.current_version_no`）获取文件路径
2. 构建 metadata jsonb
3. INSERT `report_status_log`：
   - `report_id` = NEW.id
   - `from_status` = OLD.status
   - `to_status` = NEW.status
   - `action_by` = auth.uid()
   - `action_by_name` = auth.jwt()->>'email'
   - `version_no` = NEW.current_version_no
   - `reason` = NEW.rejection_reason（`to_status = 'rejected'` 时有值，其余 NULL）
   - `metadata` = 构建的 jsonb

**不声明 SECURITY DEFINER**，以调用者身份执行，依赖现有 `rsl_insert` RLS policy。

**职责分离：**
- `trg_report_status_transition`（BEFORE UPDATE）：状态流转校验，不变
- 新触发器（AFTER UPDATE）：写日志，不做校验

### RPC：submit_report

- 删除手动 INSERT `report_status_log`（触发器接管）
- UPDATE 时追加 `SET rejection_reason = NULL`

### RPC：retract_report

- 删除手动 INSERT `report_status_log`（触发器接管）
- UPDATE 时追加 `SET rejection_reason = NULL`

### Python

- `test_submit_report.py`：`test_status_log_created` 补充 metadata 非空断言
- `test_retract_report.py`：`test_retract_submitted_report` 补充 metadata 非空断言

### 验证标准

- 状态变更后 `report_status_log` 自动写入，`metadata` 包含完整快照
- 手动 INSERT 已删除，不产生重复日志
- `rejection_reason` 在 submit/retract 时重置为 NULL
