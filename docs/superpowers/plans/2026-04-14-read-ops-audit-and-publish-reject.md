# 读操作架构审计 & 补 publish/reject 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 审计并修正读操作架构边界，补齐 SA 审批所需的 publish/reject 两个 RPC。

**Architecture:** 3 个独立变更——resolve_analyst_by_email 改直接查表、resolve_template 改查询条件、新增 publish_report/reject_report RPC。SQL 侧统一一个迁移文件。

**Tech Stack:** Supabase (PostgreSQL RPC + RLS), Python (supabase-py), pytest

**Spec:** `docs/superpowers/specs/2026-04-14-read-ops-audit-and-publish-reject-design.md`

---

### Task 1: resolve_analyst_by_email → 直接查表

**Files:**
- Modify: `skills/neolyst/scripts/analyst.py`
- Test: `skills/neolyst/tests/test_analyst.py`（现有测试应直接通过）

- [ ] **Step 1: 修改 analyst.py**

```python
"""
analyst.py — Neolyst analyst 查询模块。
"""

from supabase import Client


def resolve_analyst_by_email(client: Client, email: str) -> dict:
    """
    根据邮箱查询并返回 analyst 记录。

    邮箱大小写不敏感，内部统一 lowercase/strip。
    is_active=False 的分析师抛出 ValueError。

    Args:
        client: 已认证的 Supabase client
        email: 分析师邮箱

    Returns:
        dict: analyst 记录全部字段

    Raises:
        ValueError: 找不到分析师，或分析师已停用
    """
    email_lower = email.strip().lower()
    resp = (
        client.table("analyst")
        .select("*")
        .eq("email", email_lower)
        .execute()
    )
    if not resp.data:
        raise ValueError(f"找不到分析师：{email}")
    record = resp.data[0]
    if not record.get("is_active", True):
        raise ValueError(f"分析师已停用：{email}")
    return record
```

- [ ] **Step 2: 运行现有测试验证行为不变**

Run: `cd /mnt/c/_code/neoskills && uv run pytest skills/neolyst/tests/test_analyst.py -v`
Expected: 全部 PASS（test_found_returns_full_record, test_email_is_case_insensitive, test_not_found_raises_value_error, test_inactive_raises_value_error）

- [ ] **Step 3: 提交**

```bash
git add skills/neolyst/scripts/analyst.py
git commit -m "refactor: resolve_analyst_by_email 改为直接查表

不再依赖 RPC，Python 侧做 lower/strip 和 is_active 校验。
"
```

---

### Task 2: resolve_template 改按 report_type + language 查询

**Files:**
- Modify: `skills/neolyst/scripts/template.py:90-96`
- Test: `skills/neolyst/tests/test_template.py`（现有测试应直接通过）

- [ ] **Step 1: 修改 template.py 中 resolve_template 的查询条件**

将 L90-96 从：
```python
    record_id = f"{report_type}_{language}"
    resp = (
        client.table("report_template")
        .select("template_file_path, schema_file_path")
        .eq("id", record_id)
        .execute()
    )
```

改为：
```python
    resp = (
        client.table("report_template")
        .select("template_file_path, schema_file_path")
        .eq("report_type", report_type)
        .eq("language", language)
        .execute()
    )
```

同时更新函数 docstring 中的说明，删除"按 {report_type}_{language} 组合主键查询"的描述。

- [ ] **Step 2: 运行现有模板测试**

Run: `cd /mnt/c/_code/neoskills && uv run pytest skills/neolyst/tests/test_template.py -v`
Expected: 全部 PASS

- [ ] **Step 3: 提交**

```bash
git add skills/neolyst/scripts/template.py
git commit -m "refactor: resolve_template 改按 report_type+language 查询

不再拼 id，让 Python 侧不依赖 id 拼接规则。
"
```

---

### Task 3: SQL 迁移（DROP 旧 RPC + 修改 RLS + 新增 publish/reject）

**Files:**
- Create: `supabase/migrations/<timestamp>_read_ops_audit_and_publish_reject.sql`

- [ ] **Step 1: 创建迁移文件**

Run: `cd /mnt/c/_code/neoskills && npx supabase migration new read_ops_audit_and_publish_reject`

- [ ] **Step 2: 编写迁移 SQL**

```sql
-- 1. 删除 resolve_analyst_by_email（已改为 Python 直接查表）
DROP FUNCTION IF EXISTS public.resolve_analyst_by_email(text);

-- 2. 修改 report_update RLS policy，追加 SA 权限
DROP POLICY IF EXISTS report_update ON public.report;

CREATE POLICY report_update ON public.report
FOR UPDATE TO authenticated
USING (
    (public.current_app_role() = 'admin')
    OR (public.current_app_role() = 'analyst'
        AND owner_user_id = auth.uid()
        AND status = ANY (ARRAY['draft', 'submitted', 'rejected']))
    OR (public.current_app_role() = 'sa'
        AND status = 'submitted')
)
WITH CHECK (
    (public.current_app_role() = 'admin')
    OR (public.current_app_role() = 'analyst'
        AND owner_user_id = auth.uid()
        AND status = 'draft')
    OR (public.current_app_role() = 'sa'
        AND status IN ('published', 'rejected'))
);

-- 3. publish_report：submitted → published
CREATE OR REPLACE FUNCTION public.publish_report(p_report_id uuid)
RETURNS TABLE(report_id uuid, status text)
LANGUAGE plpgsql
AS $$
declare
    v_status text;
begin
    select status into v_status
      from public.report
     where id = p_report_id;

    if not found then
        raise exception '报告不存在: %', p_report_id;
    end if;

    if v_status <> 'submitted' then
        raise exception '报告状态为 %，无法发布（仅 submitted 可发布）', v_status;
    end if;

    update public.report
       set status = 'published',
           published_by = auth.uid(),
           published_at = now()
     where id = p_report_id;

    return query select p_report_id, 'published'::text;
end;
$$;

COMMENT ON FUNCTION public.publish_report(uuid) IS '将 submitted 报告发布为 published，记录 published_by 和 published_at。';

-- 4. reject_report：submitted → rejected
CREATE OR REPLACE FUNCTION public.reject_report(
    p_report_id uuid,
    p_rejection_reason text
)
RETURNS TABLE(report_id uuid, status text)
LANGUAGE plpgsql
AS $$
declare
    v_status text;
begin
    if coalesce(btrim(p_rejection_reason), '') = '' then
        raise exception '退回原因不能为空';
    end if;

    select status into v_status
      from public.report
     where id = p_report_id;

    if not found then
        raise exception '报告不存在: %', p_report_id;
    end if;

    if v_status <> 'submitted' then
        raise exception '报告状态为 %，无法退回（仅 submitted 可退回）', v_status;
    end if;

    update public.report
       set status = 'rejected',
           rejection_reason = p_rejection_reason
     where id = p_report_id;

    return query select p_report_id, 'rejected'::text;
end;
$$;

COMMENT ON FUNCTION public.reject_report(uuid, text) IS '将 submitted 报告退回为 rejected，必填退回原因。';

-- 5. 权限授予
REVOKE ALL ON FUNCTION public.publish_report(uuid) FROM PUBLIC;
GRANT ALL ON FUNCTION public.publish_report(uuid) TO authenticated;
GRANT ALL ON FUNCTION public.publish_report(uuid) TO service_role;

REVOKE ALL ON FUNCTION public.reject_report(uuid, text) FROM PUBLIC;
GRANT ALL ON FUNCTION public.reject_report(uuid, text) TO authenticated;
GRANT ALL ON FUNCTION public.reject_report(uuid, text) TO service_role;
```

- [ ] **Step 3: 应用迁移并验证**

Run: `cd /mnt/c/_code/neoskills && npx supabase db reset`

验证 RPC 已创建：
```sql
SELECT proname FROM pg_proc WHERE proname IN ('publish_report', 'reject_report');
-- 应返回 2 行
```

验证旧 RPC 已删除：
```sql
SELECT proname FROM pg_proc WHERE proname = 'resolve_analyst_by_email';
-- 应返回 0 行
```

- [ ] **Step 4: 提交**

```bash
git add supabase/migrations/
git commit -m "feat: 迁移 - 删 resolve_analyst_by_email，加 publish/reject RPC，扩展 SA RLS"
```

---

### Task 4: publish_report Python 实现（TDD）

**依赖：** Task 3（迁移必须先执行）

**Files:**
- Modify: `skills/neolyst/scripts/report.py`
- Create: `skills/neolyst/tests/test_publish_report.py`

- [ ] **Step 1: 编写测试**

```python
"""
test_publish_report.py — publish_report 集成测试。

需要 admin 或 SA 角色执行（RLS 限制）。
"""
import uuid
import pytest


@pytest.fixture(scope="module")
def publish_coverage_id(neolyst_client, test_sector_id, test_analyst_email):
    from skills.neolyst.scripts import coverage as cov

    _suffix = uuid.uuid4().hex[:6].upper()
    cov_id = cov.create_coverage(
        neolyst_client,
        ticker=f"PUB{_suffix}",
        english_name=f"Publish Test Co {_suffix}",
        sector_id=test_sector_id,
        isin=f"HK{_suffix}{'0' * (10 - len(_suffix))}",
        country_of_domicile="Hong Kong",
        analysts=[{"analyst_email": test_analyst_email, "author_order": 1}],
    )
    yield cov_id
    neolyst_client.table("coverage").delete().eq("id", cov_id).execute()


class TestPublishReport:
    def test_publish_submitted_report(self, neolyst_client, publish_coverage_id, test_analyst_email, tmp_path):
        from skills.neolyst.scripts.report import publish_report as pr

        submitted = _create_submitted_report(
            neolyst_client, publish_coverage_id, tmp_path / "publish_happy",
            "Publish Test", test_analyst_email,
        )
        report_id = submitted["report_id"]

        try:
            result = pr(neolyst_client, report_id)

            assert result["status"] == "published"
            uuid.UUID(result["report_id"])

            resp = (
                neolyst_client.table("report")
                .select("status, published_by, published_at")
                .eq("id", report_id)
                .execute()
            )
            row = resp.data[0]
            assert row["status"] == "published"
            assert row["published_by"] is not None
            assert row["published_at"] is not None

            log_resp = (
                neolyst_client.table("report_status_log")
                .select("*")
                .eq("report_id", report_id)
                .eq("to_status", "published")
                .execute()
            )
            assert log_resp.data
            log = log_resp.data[0]
            assert log["from_status"] == "submitted"
            assert log["to_status"] == "published"
        finally:
            neolyst_client.table("report").delete().eq("id", report_id).execute()

    def test_publish_draft_raises(self, neolyst_client, publish_coverage_id, test_analyst_email, tmp_path):
        from skills.neolyst.scripts.report import save_report, publish_report as pr

        saved = save_report(neolyst_client, _base_report_payload(
            test_analyst_email,
            title="Publish Draft Test",
            ticker="PUBDRAFT",
            investment_thesis="Test investment thesis",
            coverage_id=publish_coverage_id,
        ))
        try:
            with pytest.raises(ValueError, match="无法发布"):
                pr(neolyst_client, saved["report_id"])
        finally:
            neolyst_client.table("report").delete().eq("id", saved["report_id"]).execute()

    def test_publish_already_published_raises(self, neolyst_client, publish_coverage_id, test_analyst_email, tmp_path):
        from skills.neolyst.scripts.report import publish_report as pr

        submitted = _create_submitted_report(
            neolyst_client, publish_coverage_id, tmp_path / "double_publish",
            "Double Publish Test", test_analyst_email,
        )
        report_id = submitted["report_id"]

        try:
            pr(neolyst_client, report_id)
            with pytest.raises(ValueError, match="无法发布"):
                pr(neolyst_client, report_id)
        finally:
            neolyst_client.table("report").delete().eq("id", report_id).execute()

    def test_publish_nonexistent_raises(self, neolyst_client):
        from skills.neolyst.scripts.report import publish_report as pr

        with pytest.raises(ValueError, match="报告不存在"):
            pr(neolyst_client, str(uuid.uuid4()))
```

- [ ] **Step 2: 运行测试（RED）**

Run: `cd /mnt/c/_code/neoskills && uv run pytest skills/neolyst/tests/test_publish_report.py -v`
Expected: FAIL（`import publish_report` 或函数不存在）

- [ ] **Step 3: 在 report.py 中添加 publish_report**

在 `retract_report` 函数后追加：

```python
def publish_report(client: Client, report_id: str) -> dict:
    """发布报告，返回 {"report_id": str, "status": "published"}。"""
    row = rpc.single_row(rpc.call_rpc(client, "publish_report", {
        "p_report_id": report_id,
    }))
    return {
        "report_id": str(row["report_id"]),
        "status": row["status"],
    }
```

- [ ] **Step 4: 运行测试（GREEN）**

Run: `cd /mnt/c/_code/neoskills && uv run pytest skills/neolyst/tests/test_publish_report.py -v`
Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git add skills/neolyst/scripts/report.py skills/neolyst/tests/test_publish_report.py
git commit -m "feat: 实现 publish_report Python 接口及集成测试"
```

---

### Task 5: reject_report Python 实现（TDD）

**依赖：** Task 3（迁移必须先执行）

**Files:**
- Modify: `skills/neolyst/scripts/report.py`
- Create: `skills/neolyst/tests/test_reject_report.py`

- [ ] **Step 1: 编写测试**

```python
"""
test_reject_report.py — reject_report 集成测试。

需要 admin 或 SA 角色执行（RLS 限制）。
"""
import uuid
import pytest


@pytest.fixture(scope="module")
def reject_coverage_id(neolyst_client, test_sector_id, test_analyst_email):
    from skills.neolyst.scripts import coverage as cov

    _suffix = uuid.uuid4().hex[:6].upper()
    cov_id = cov.create_coverage(
        neolyst_client,
        ticker=f"REJ{_suffix}",
        english_name=f"Reject Test Co {_suffix}",
        sector_id=test_sector_id,
        isin=f"HK{_suffix}{'0' * (10 - len(_suffix))}",
        country_of_domicile="Hong Kong",
        analysts=[{"analyst_email": test_analyst_email, "author_order": 1}],
    )
    yield cov_id
    neolyst_client.table("coverage").delete().eq("id", cov_id).execute()


class TestRejectReport:
    def test_reject_submitted_report(self, neolyst_client, reject_coverage_id, test_analyst_email, tmp_path):
        from skills.neolyst.scripts.report import reject_report as rr

        submitted = _create_submitted_report(
            neolyst_client, reject_coverage_id, tmp_path / "reject_happy",
            "Reject Test", test_analyst_email,
        )
        report_id = submitted["report_id"]

        try:
            result = rr(neolyst_client, report_id, reason="格式不符合要求")

            assert result["status"] == "rejected"
            uuid.UUID(result["report_id"])

            resp = (
                neolyst_client.table("report")
                .select("status, rejection_reason")
                .eq("id", report_id)
                .execute()
            )
            row = resp.data[0]
            assert row["status"] == "rejected"
            assert row["rejection_reason"] == "格式不符合要求"

            log_resp = (
                neolyst_client.table("report_status_log")
                .select("*")
                .eq("report_id", report_id)
                .eq("to_status", "rejected")
                .execute()
            )
            assert log_resp.data
            log = log_resp.data[0]
            assert log["from_status"] == "submitted"
            assert log["to_status"] == "rejected"
            assert log["reason"] == "格式不符合要求"
        finally:
            neolyst_client.table("report").delete().eq("id", report_id).execute()

    def test_reject_without_reason_raises(self, neolyst_client, reject_coverage_id, test_analyst_email, tmp_path):
        from skills.neolyst.scripts.report import reject_report as rr

        submitted = _create_submitted_report(
            neolyst_client, reject_coverage_id, tmp_path / "reject_no_reason",
            "Reject No Reason Test", test_analyst_email,
        )
        report_id = submitted["report_id"]

        try:
            with pytest.raises(ValueError, match="退回原因"):
                rr(neolyst_client, report_id, reason="")
        finally:
            neolyst_client.table("report").delete().eq("id", report_id).execute()

    def test_reject_draft_raises(self, neolyst_client, reject_coverage_id, test_analyst_email, tmp_path):
        from skills.neolyst.scripts.report import save_report, reject_report as rr

        saved = save_report(neolyst_client, _base_report_payload(
            test_analyst_email,
            title="Reject Draft Test",
            ticker="REJDRAFT",
            investment_thesis="Test investment thesis",
            coverage_id=reject_coverage_id,
        ))
        try:
            with pytest.raises(ValueError, match="无法退回"):
                rr(neolyst_client, saved["report_id"], reason="test reason")
        finally:
            neolyst_client.table("report").delete().eq("id", saved["report_id"]).execute()

    def test_reject_nonexistent_raises(self, neolyst_client):
        from skills.neolyst.scripts.report import reject_report as rr

        with pytest.raises(ValueError, match="报告不存在"):
            rr(neolyst_client, str(uuid.uuid4()), reason="test reason")
```

- [ ] **Step 2: 运行测试（RED）**

Run: `cd /mnt/c/_code/neoskills && uv run pytest skills/neolyst/tests/test_reject_report.py -v`
Expected: FAIL

- [ ] **Step 3: 在 report.py 中添加 reject_report**

在 `publish_report` 函数后追加：

```python
def reject_report(client: Client, report_id: str, reason: str) -> dict:
    """退回报告，返回 {"report_id": str, "status": "rejected"}。"""
    row = rpc.single_row(rpc.call_rpc(client, "reject_report", {
        "p_report_id": report_id,
        "p_rejection_reason": reason,
    }))
    return {
        "report_id": str(row["report_id"]),
        "status": row["status"],
    }
```

- [ ] **Step 4: 运行测试（GREEN）**

Run: `cd /mnt/c/_code/neoskills && uv run pytest skills/neolyst/tests/test_reject_report.py -v`
Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git add skills/neolyst/scripts/report.py skills/neolyst/tests/test_reject_report.py
git commit -m "feat: 实现 reject_report Python 接口及集成测试"
```

---

### Task 6: 文档更新

**Files:**
- Modify: `skills/neolyst/SKILL.md`
- Modify: `skills/neolyst/references/interfaces.md`

- [ ] **Step 1: 更新 SKILL.md 接口表**

在接口表中：
- 修改 #1 `resolve_analyst_by_email` 说明为"直接查表，Python 侧做 lower/strip 和 is_active 校验"
- 追加 #13 `publish_report(client, report_id)` → `report` — 将 submitted 报告发布为 published
- 追加 #14 `reject_report(client, report_id, reason)` → `report` — 将 submitted 报告退回为 rejected

业务约束中追加：
- `publish_report`：仅 submitted 状态可发布，由 SA 角色执行
- `reject_report`：仅 submitted 状态可退回，必填退回原因，由 SA 角色执行

参考文件数量更新为 14。

- [ ] **Step 2: 更新 references/interfaces.md**

更新 `resolve_analyst_by_email` 段落：删除"Supabase RPC 侧执行"描述。

追加 `publish_report` 和 `reject_report` 两个接口的完整签名、参数、返回值和示例。

- [ ] **Step 3: 提交**

```bash
git add skills/neolyst/SKILL.md skills/neolyst/references/interfaces.md
git commit -m "docs: 更新 SKILL.md 和 interfaces.md，补 publish/reject 接口文档"
```
