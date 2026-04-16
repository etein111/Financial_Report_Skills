# report.is_active 字段 + deactivate_report 接口 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 report 表加 is_active 字段，实现 deactivate_report 接口。

**Architecture:** migration 加字段（boolean NOT NULL DEFAULT true），Python 侧直接查表 update（和 set_analyst_active 一致的模式），不走 RPC。

**Tech Stack:** Supabase migration SQL, Python supabase-py, pytest

---

### Task 1: 创建 migration — report 表增加 is_active 字段

**Files:**
- Create: `supabase/migrations/<timestamp>_add_report_is_active.sql`

- [ ] **Step 1: 用 supabase CLI 生成 migration 文件**

Run: `cd /mnt/c/_code/neoskills && supabase migration new add_report_is_active`

- [ ] **Step 2: 写入 SQL**

在生成的 migration 文件中写入：

```sql
ALTER TABLE report ADD COLUMN is_active boolean NOT NULL DEFAULT true;

COMMENT ON COLUMN report.is_active IS '软删除标记，true=正常，false=废弃。不参与状态机流转。';
```

- [ ] **Step 3: 本地验证 migration**

Run: `cd /mnt/c/_code/neoskills && supabase db reset`
Expected: 成功，report 表包含 is_active 列，现有数据全部为 true。

- [ ] **Step 4: Commit**

```bash
git add supabase/migrations/*_add_report_is_active.sql
git commit -m "feat: report 表增加 is_active 字段（软废弃标记）"
```

---

### Task 2: 写 deactivate_report 测试

**Files:**
- Create: `skills/neolyst/tests/test_deactivate_report.py`

- [ ] **Step 1: 创建测试文件**

```python
"""
test_deactivate_report.py — deactivate_report 集成测试。
"""
import uuid
import pytest


class TestDeactivateReport:
    def test_deactivate_draft_report(self, neolyst_client, retract_coverage_id, test_analyst_email, tmp_path):
        from skills.neolyst.scripts.report import save_report
        from skills.neolyst.scripts.report import deactivate_report

        saved = save_report(neolyst_client, _base_report_payload(
            test_analyst_email,
            title="Deactivate Draft Test",
            ticker="DEACT01",
            investment_thesis="Test thesis",
            coverage_id=retract_coverage_id,
            rating="OUTPERFORM",
            target_price=100.0,
        ))
        report_id = saved["report_id"]

        try:
            result = deactivate_report(neolyst_client, report_id)

            assert result["report_id"] == report_id
            assert result["is_active"] is False

            resp = (
                neolyst_client.table("report")
                .select("is_active")
                .eq("id", report_id)
                .execute()
            )
            assert resp.data[0]["is_active"] is False
        finally:
            neolyst_client.table("report").delete().eq("id", report_id).execute()

    def test_deactivate_nonexistent_raises(self, neolyst_client):
        from skills.neolyst.scripts.report import deactivate_report

        with pytest.raises(ValueError, match="报告不存在"):
            deactivate_report(neolyst_client, str(uuid.uuid4()))

    def test_deactivate_already_inactive_raises(self, neolyst_client, retract_coverage_id, test_analyst_email, tmp_path):
        from skills.neolyst.scripts.report import save_report
        from skills.neolyst.scripts.report import deactivate_report

        saved = save_report(neolyst_client, _base_report_payload(
            test_analyst_email,
            title="Deactivate Twice Test",
            ticker="DEACT02",
            investment_thesis="Test thesis",
            coverage_id=retract_coverage_id,
            rating="OUTPERFORM",
            target_price=100.0,
        ))
        report_id = saved["report_id"]

        try:
            deactivate_report(neolyst_client, report_id)
            with pytest.raises(ValueError, match="报告已废弃"):
                deactivate_report(neolyst_client, report_id)
        finally:
            neolyst_client.table("report").delete().eq("id", report_id).execute()
```

注意：`_base_report_payload` 和 `retract_coverage_id` 来自 `conftest.py` 共享 helpers。`retract_coverage_id` fixture 会创建临时 coverage，测试结束后删除。

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /mnt/c/_code/neoskills && uv run pytest skills/neolyst/tests/test_deactivate_report.py -v`
Expected: FAIL — `ImportError: cannot import name 'deactivate_report'`

- [ ] **Step 3: Commit 测试文件**

```bash
git add skills/neolyst/tests/test_deactivate_report.py
git commit -m "test: deactivate_report 集成测试（RED）"
```

---

### Task 3: 实现 deactivate_report

**Files:**
- Modify: `skills/neolyst/scripts/report.py`

- [ ] **Step 1: 在 report.py 末尾添加 deactivate_report 函数**

```python
def deactivate_report(client: Client, report_id: str) -> dict:
    """废弃报告，设 is_active=False。返回 {"report_id": str, "is_active": False}。"""
    resp = (
        client.table("report")
        .update({"is_active": False})
        .eq("id", report_id)
        .eq("is_active", True)
        .execute()
    )
    if not resp.data:
        exists = (
            client.table("report")
            .select("id,is_active")
            .eq("id", report_id)
            .execute()
        )
        if not exists.data:
            raise ValueError(f"报告不存在：{report_id}")
        raise ValueError(f"报告已废弃：{report_id}")
    return {"report_id": report_id, "is_active": False}
```

设计说明：
- `.eq("is_active", True)` 作为 update 条件，只有 is_active=true 的行会被更新
- 更新后 resp.data 为空时，二次查询区分"不存在"和"已废弃"
- 和 `set_analyst_active` 模式一致（直接查表 update）

- [ ] **Step 2: 运行测试确认通过**

Run: `cd /mnt/c/_code/neoskills && uv run pytest skills/neolyst/tests/test_deactivate_report.py -v`
Expected: 3 tests PASS

- [ ] **Step 3: Commit**

```bash
git add skills/neolyst/scripts/report.py
git commit -m "feat: deactivate_report 接口 — 软废弃报告（admin only）"
```

---

### Task 4: 更新 interfaces.md 文档

**Files:**
- Modify: `skills/neolyst/references/interfaces.md`

- [ ] **Step 1: 在 reject_report 接口之后、错误处理策略之前，新增 ## 16. deactivate_report 章节**

内容：

```markdown
## 16. deactivate_report

将报告标记为废弃（is_active = false），不影响 status 状态机。

```python
from skills.neolyst.scripts.report import deactivate_report

result = deactivate_report(client, report_id)
# 返回：{"report_id": str, "is_active": False}
# 报告不存在：抛出 ValueError（"报告不存在：{report_id}"）
# 报告已废弃：抛出 ValueError（"报告已废弃：{report_id}"）
```

- 直接查表 update，不走 RPC
- admin only（受 report 表 RLS 约束）
- 废弃后查询报告需加 `.eq("is_active", True)` 过滤
```

- [ ] **Step 2: Commit**

```bash
git add skills/neolyst/references/interfaces.md
git commit -m "docs: interfaces.md 新增 deactivate_report 接口说明"
```
