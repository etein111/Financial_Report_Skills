# Neolyst Iter 5: validators + submit_report 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 `validate_draft`（Python 侧多项校验，全量收集错误）和 `submit_report`（Supabase RPC 原子提交 + 状态日志），支持将合法 draft 报告提交为 submitted。

**Architecture:**
- **Supabase 侧**：新增 `submit_report` RPC，原子执行 `report.status` 更新 + `report_status_log` 插入，`action_by_name` 使用 `auth.jwt() ->> 'email'`（调用者邮箱）。
- **Python 侧 `validators.py`**：纯 SELECT 查询，收集全部校验错误后一次性抛出 ValueError；不写 RPC。
- **Python 侧 `submit_report.py`**：先调 `validate_draft`，通过后调 `submit_report` RPC，返回 `{report_id, version_no, status}`。

**Tech Stack:** Python 3.12+, supabase-py, pytest, uuid

**已确认的设计决策：**
- `company` 类型报告：`coverage_id` 必填；其他类型 `coverage_id` 可为空
- `sector_id`、`region_code`：有值时验证存在性，无值时跳过
- validators 只做 SELECT，不走 RPC，Python 侧实现
- `action_by_name` 字段填调用者邮箱（`auth.jwt() ->> 'email'`）
- submit 是 Supabase RPC，Python 侧做薄封装

---

## 文件结构

| 文件 | 操作 | 说明 |
|------|------|------|
| `supabase/migrations/20260410000100_080_submit_report_function.sql` | 新建 | `submit_report` RPC |
| `skills/neolyst/scripts/validators.py` | 新建 | `validate_draft` 函数，Python 侧多项校验 |
| `skills/neolyst/scripts/submit_report.py` | 新建 | `submit_report` 函数，调用 validators + RPC |
| `skills/neolyst/tests/test_validators.py` | 新建 | validators 集成测试（11 个） |
| `skills/neolyst/tests/test_submit_report.py` | 新建 | submit_report 集成测试（5 个） |
| `skills/neolyst/SKILL.md` | 修改 | validators 和 submit_report 标记为 ✅ 已实现 |
| `docs/skills_neolyst_design.md` | 修改 | 补充 submit_report 设计说明 |
| `plans/2026-04-07-neolyst-skill-roadmap.md` | 修改 | 标记 Iter 5 完成 |

---

## 背景与约束

**report 表关键字段：** `id`、`title`（NOT NULL）、`report_type`（NOT NULL）、`status`（default 'draft'）、`current_version_no`、`coverage_id`（nullable）、`ticker`、`sector_id`（nullable）、`region_code`（nullable）、`rating`、`target_price`、`investment_thesis`（nullable）、`report_language`（nullable）、`contact_person`（nullable）

**report_version 表：** `(report_id, version_no)` 唯一；`word_file_path`、`pdf_file_path` 可为空

**report_status_log 表：** `action_by uuid`、`action_by_name text`（nullable）、`from_status`、`to_status`、`version_no`；CHECK：to_status='rejected' 时 reason 必填

**状态流转：** `draft → submitted`，`rejected → submitted`；其他状态不可提交

**RLS：**
- `report_update`：admin 无条件；analyst 需 owner_user_id = auth.uid() 且 status in ('draft','submitted')
- `rsl_insert`：admin 无条件；analyst 需 from_status='draft' AND to_status='submitted' 且为 owner
- `rv_insert`：admin 无条件；analyst 需 owner 且 status in ('draft','submitted')

**测试账号：** `yangxue@opendelp.com` / `Admin123`（admin 角色，在 analyst 表中且 is_active=true）

**validators 校验规则（按序，全量收集）：**
1. report 存在，status in ('draft', 'rejected')
2. 指定 version_no 的 version 存在
3. version.word_file_path 非空
4. version.pdf_file_path 非空
5. report.title 非空
6. report.report_type 非空
7. report.report_language 非空
8. report.investment_thesis 非空
9. report.contact_person 非空
10. report_analyst 不为空（至少一个分析师）
11. report.contact_person 在 report_analyst.analyst_email 列表中
12. 每个 report_analyst.analyst_email 在 analyst 表中存在且 is_active=true
13. 若 report_type == 'company'：coverage_id 非空且在 coverage 表中存在
14. 若 sector_id 非空：在 sector 表中存在
15. 若 region_code 非空：在 region 表中存在

---

## Task 1: Supabase 迁移 — submit_report RPC

**Files:**
- Create: `supabase/migrations/20260410000100_080_submit_report_function.sql`

- [ ] **Step 1: 创建迁移文件**

```sql
-- 20260410000100_080_submit_report_function.sql
-- 1. 扩展 report_status_is_valid：加 rejected → submitted
-- 2. 更新 report_update policy：using 子句加 rejected
-- 3. 更新 rsl_insert policy：analyst 可从 rejected 提交
-- 4. submit_report RPC：draft/rejected → submitted，写入状态日志

-- ----------------------------------------------------------------
-- 1. 扩展状态流转合法性函数（加 rejected → submitted）
-- ----------------------------------------------------------------

create or replace function public.report_status_is_valid(from_status text, to_status text)
returns boolean
language sql
immutable
as $$
    select (from_status = 'draft' and to_status = 'submitted')
        or (from_status = 'submitted' and to_status in ('published', 'rejected'))
        or (from_status = 'rejected' and to_status in ('draft', 'submitted'))
$$;

comment on function public.report_status_is_valid(text, text) is
'判断报告状态流转是否合法（IMMUTABLE）。合法路径：draft→submitted、submitted→published、submitted→rejected、rejected→draft、rejected→submitted。';

-- ----------------------------------------------------------------
-- 2. 更新 report_update policy（using 子句加 rejected，允许 analyst 更新 rejected 报告）
-- ----------------------------------------------------------------

drop policy if exists report_update on public.report;

create policy report_update
on public.report
for update
to authenticated
using (
    (public.current_app_role() = 'admin'::text)
    or (
        (public.current_app_role() = 'analyst'::text)
        and (owner_user_id = auth.uid())
        and (status = any (array['draft'::text, 'submitted'::text, 'rejected'::text]))
    )
)
with check (
    (public.current_app_role() = 'admin'::text)
    or (
        (public.current_app_role() = 'analyst'::text)
        and (owner_user_id = auth.uid())
        and (status = any (array['draft'::text, 'submitted'::text, 'rejected'::text]))
    )
);

-- ----------------------------------------------------------------
-- 3. 更新 rsl_insert policy（analyst 可从 rejected 提交）
-- ----------------------------------------------------------------

drop policy if exists rsl_insert on public.report_status_log;

create policy rsl_insert
on public.report_status_log
for insert
to authenticated
with check (
    (public.current_app_role() = 'admin'::text)
    or (
        (public.current_app_role() = 'sa'::text)
        and (from_status = any (array['submitted'::text, 'rejected'::text]))
    )
    or (
        (public.current_app_role() = 'analyst'::text)
        and (from_status = any (array['draft'::text, 'rejected'::text]))
        and (to_status = 'submitted'::text)
        and exists (
            select 1 from public.report r
            where r.id = report_status_log.report_id
              and r.owner_user_id = auth.uid()
        )
    )
);

-- ----------------------------------------------------------------
-- 4. submit_report RPC
-- ----------------------------------------------------------------

create or replace function public.submit_report(
    p_report_id  uuid,
    p_version_no integer
)
returns table(report_id uuid, version_no integer, status text)
language plpgsql
as $$
declare
    v_current_status text;
    v_action_email   text;
begin
    select r.status into v_current_status
    from public.report r
    where r.id = p_report_id;

    if not found then
        raise exception '报告不存在: %', p_report_id;
    end if;

    if v_current_status not in ('draft', 'rejected') then
        raise exception '报告状态为 %，无法提交（仅 draft/rejected 可提交）', v_current_status;
    end if;

    v_action_email := auth.jwt() ->> 'email';

    update public.report
    set status = 'submitted'
    where id = p_report_id;

    insert into public.report_status_log (
        report_id, from_status, to_status,
        action_by, action_by_name, version_no
    ) values (
        p_report_id, v_current_status, 'submitted',
        auth.uid(), v_action_email, p_version_no
    );

    return query select p_report_id, p_version_no, 'submitted'::text;
end;
$$;

comment on function public.submit_report is
'将 draft/rejected 状态的报告提交为 submitted。原子更新 report.status 并写入 report_status_log。
action_by_name 填调用者邮箱（auth.jwt() ->> email）。Python 侧在调用前须先通过 validate_draft。';

revoke execute on function public.submit_report from public, anon;
grant execute on function public.submit_report to authenticated;
```

- [ ] **Step 2: 应用迁移**

```bash
cd /mnt/c/_code/neoskills
supabase db reset
```

Expected: 末尾输出 `Finished supabase db reset on branch main.`，无 ERROR。

- [ ] **Step 3: 验证 RPC 存在**

```bash
cd /mnt/c/_code/neoskills
uv run python -c "
from skills.neolyst.scripts import connection
import uuid
client = connection.get_client()
fake_id = str(uuid.uuid4())
try:
    client.rpc('submit_report', {'p_report_id': fake_id, 'p_version_no': 1}).execute()
except Exception as e:
    print('submit_report 错误（期望报告不存在）:', str(e)[:120])
"
```

Expected: 输出含 `报告不存在`

---

## Task 2: 实现 validators.py

**Files:**
- Create: `skills/neolyst/scripts/validators.py`

- [ ] **Step 1: 创建 validators.py**

```python
"""
validators.py — Neolyst draft 报告提交前校验。

校验规则（全量收集，一次性抛出所有错误）：
1. report 存在且 status in ('draft', 'rejected')
2. 指定版本存在
3. word_file_path / pdf_file_path 非空
4. 必填字段：title / report_type / report_language / investment_thesis / contact_person
5. 至少一个分析师；contact_person 在分析师列表中
6. 每个分析师在 analyst 表中存在且 is_active
7. company 类型：coverage_id 必填且存在
8. sector_id / region_code：有值时验证存在性

业务逻辑全部在 Python 侧实现，仅做 SELECT 查询，不调用 RPC。
"""

from supabase import Client


def validate_draft(client: Client, report_id: str, version_no: int) -> dict:
    """
    校验 draft 报告指定版本是否满足提交条件。

    Args:
        client: 已认证的 Supabase client
        report_id: 报告 UUID 字符串
        version_no: 要提交的版本号（整数）

    Returns:
        dict: {"report_id": report_id, "version_no": version_no}（校验通过时）

    Raises:
        ValueError: 校验失败，消息列出所有失败项，以"；"分隔
    """
    errors: list[str] = []

    # 1. report 存在性与状态
    report_resp = client.table("report").select("*").eq("id", report_id).execute()
    if not report_resp.data:
        raise ValueError(f"报告不存在: {report_id}")
    report = report_resp.data[0]

    if report["status"] not in ("draft", "rejected"):
        errors.append(f"报告状态为 {report['status']}，仅 draft/rejected 可提交")

    # 2. version 存在性
    version_resp = (
        client.table("report_version")
        .select("word_file_path, pdf_file_path")
        .eq("report_id", report_id)
        .eq("version_no", version_no)
        .execute()
    )
    if not version_resp.data:
        errors.append(f"版本 v{version_no} 不存在")
        version = None
    else:
        version = version_resp.data[0]

    # 3. 文件路径
    if version:
        if not version.get("word_file_path"):
            errors.append("缺少 Word 文件路径（word_file_path）")
        if not version.get("pdf_file_path"):
            errors.append("缺少 PDF 文件路径（pdf_file_path）")

    # 4. 必填字段
    required_fields = {
        "title": "标题（title）",
        "report_type": "报告类型（report_type）",
        "report_language": "报告语言（report_language）",
        "investment_thesis": "投资论点（investment_thesis）",
        "contact_person": "联系人（contact_person）",
    }
    for field, label in required_fields.items():
        if not report.get(field):
            errors.append(f"缺少必填字段：{label}")

    # 5. 分析师列表
    analysts_resp = (
        client.table("report_analyst")
        .select("analyst_email")
        .eq("report_id", report_id)
        .execute()
    )
    analyst_emails = [a["analyst_email"] for a in analysts_resp.data]
    if not analyst_emails:
        errors.append("报告没有分析师（report_analyst 为空）")

    # 6. contact_person 必须在分析师列表中（大小写不敏感）
    contact = report.get("contact_person")
    if contact and analyst_emails and contact.lower() not in analyst_emails:
        errors.append(f"contact_person（{contact}）不在本报告分析师列表中")

    # 7. 每个分析师必须存在且 is_active
    for email in analyst_emails:
        a_resp = (
            client.table("analyst")
            .select("is_active")
            .eq("email", email)
            .execute()
        )
        if not a_resp.data:
            errors.append(f"分析师不存在：{email}")
        elif not a_resp.data[0]["is_active"]:
            errors.append(f"分析师已停用：{email}")

    # 8. company 类型：coverage_id 必填且存在
    if report.get("report_type") == "company":
        coverage_id = report.get("coverage_id")
        if not coverage_id:
            errors.append("公司类报告（company）必须关联 coverage_id")
        else:
            cov_resp = (
                client.table("coverage")
                .select("id")
                .eq("id", coverage_id)
                .execute()
            )
            if not cov_resp.data:
                errors.append(f"coverage 不存在：{coverage_id}")

    # 9. sector_id 存在性（有值时）
    sector_id = report.get("sector_id")
    if sector_id:
        sec_resp = client.table("sector").select("id").eq("id", sector_id).execute()
        if not sec_resp.data:
            errors.append(f"sector 不存在：{sector_id}")

    # 10. region_code 存在性（有值时）
    region_code = report.get("region_code")
    if region_code:
        reg_resp = (
            client.table("region")
            .select("code")
            .eq("code", region_code)
            .execute()
        )
        if not reg_resp.data:
            errors.append(f"region 不存在：{region_code}")

    if errors:
        raise ValueError("校验失败：" + "；".join(errors))

    return {"report_id": report_id, "version_no": version_no}
```

- [ ] **Step 2: 验证 import**

```bash
cd /mnt/c/_code/neoskills
uv run python -c "from skills.neolyst.scripts import validators; print('OK')"
```

Expected: `OK`

---

## Task 3: 实现 submit_report.py

**Files:**
- Create: `skills/neolyst/scripts/submit_report.py`

- [ ] **Step 1: 创建 submit_report.py**

```python
"""
submit_report.py — Neolyst 报告提交接口。

流程：
1. 调用 validate_draft 校验（失败则直接抛出 ValueError）
2. 调用 submit_report RPC → 原子更新 report.status + 写入 report_status_log
3. 返回 {report_id, version_no, status}

业务逻辑（状态流转、日志写入）全部在 Supabase RPC 侧，本模块只做调用串联。
"""

from supabase import Client

from skills.neolyst.scripts.validators import validate_draft


def submit_report(client: Client, report_id: str, version_no: int) -> dict:
    """
    提交 draft 报告为 submitted 状态。

    Args:
        client: 已认证的 Supabase client
        report_id: 报告 UUID 字符串
        version_no: 要提交的版本号

    Returns:
        dict: {"report_id": str, "version_no": int, "status": "submitted"}

    Raises:
        ValueError: 校验未通过（含具体失败原因）或 RPC 调用失败
    """
    # 1. 校验（失败直接抛出）
    validate_draft(client, report_id, version_no)

    # 2. 调用 submit_report RPC
    try:
        resp = client.rpc("submit_report", {
            "p_report_id": report_id,
            "p_version_no": version_no,
        }).execute()
    except Exception as e:
        raise ValueError(str(e)) from e

    row = resp.data[0]
    return {
        "report_id": str(row["report_id"]),
        "version_no": row["version_no"],
        "status": row["status"],
    }
```

- [ ] **Step 2: 验证 import**

```bash
cd /mnt/c/_code/neoskills
uv run python -c "from skills.neolyst.scripts import submit_report; print('OK')"
```

Expected: `OK`

---

## Task 4: 集成测试

**Files:**
- Create: `skills/neolyst/tests/test_validators.py`
- Create: `skills/neolyst/tests/test_submit_report.py`

- [ ] **Step 1: 创建 test_validators.py**

```python
"""
test_validators.py — validate_draft 集成测试（11 个）。

使用真实 Supabase local 实例。module-level fixture 创建一个完整合法的 draft 报告
（company 类型，含 coverage），用于 happy path 测试。各 error case 独立创建最小 draft。
"""
import uuid
from pathlib import Path

import pytest

TEST_ANALYST = "yangxue@opendelp.com"


# ── helpers ──────────────────────────────────────────────────────────

def _make_files(directory: Path) -> tuple[str, str]:
    word = directory / "report.docx"
    pdf = directory / "report.pdf"
    word.write_bytes(b"fake docx")
    pdf.write_bytes(b"fake pdf")
    return str(word), str(pdf)


def _save_draft(client, directory, overrides=None):
    """创建最小 company draft，可通过 overrides 覆盖任意字段。"""
    from skills.neolyst.scripts import draft_report

    word_path, pdf_path = _make_files(directory)
    base = {
        "report_id": None,
        "title": "Validator Test Report",
        "report_type": "company",
        "report_language": "zh",
        "investment_thesis": "test thesis",
        "contact_person": TEST_ANALYST,
        "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
        "ticker": "VTEST01",
        "coverage_id": None,  # caller must supply valid coverage_id if needed
        "sector_id": None,
        "region_code": None,
        "rating": None,
        "target_price": None,
        "report_file": word_path,
        "pdf_file": pdf_path,
        "model_file": None,
    }
    if overrides:
        base.update(overrides)
    return draft_report.save_draft_report(client, base)


def _cleanup(client, report_id):
    client.table("report").delete().eq("id", report_id).execute()


# ── module fixtures ───────────────────────────────────────────────────

@pytest.fixture(scope="module")
def test_coverage_id(neolyst_client):
    """创建测试用 coverage，测试结束后清理。"""
    from skills.neolyst.scripts import coverage as cov

    _suffix = uuid.uuid4().hex[:6].upper()
    sector_resp = neolyst_client.table("sector").select("id").eq("is_active", True).limit(1).execute()
    sector_id = sector_resp.data[0]["id"]

    cov_id = cov.create_coverage(
        neolyst_client,
        ticker=f"VLD{_suffix}",
        english_name=f"Validator Test Co {_suffix}",
        sector_id=sector_id,
        isin=f"US{_suffix}{'0' * (10 - len(_suffix))}",
        country_of_domicile="China",
        analysts=[{"analyst_email": TEST_ANALYST, "author_order": 1}],
    )
    yield cov_id
    neolyst_client.table("coverage").delete().eq("id", cov_id).execute()


@pytest.fixture(scope="module")
def valid_report(neolyst_client, test_coverage_id, tmp_path_factory):
    """完整合法的 company draft（含 coverage_id）。模块结束后清理。"""
    d = tmp_path_factory.mktemp("validators_valid")
    result = _save_draft(neolyst_client, d, {"coverage_id": test_coverage_id})
    yield result
    _cleanup(neolyst_client, result["report_id"])


# ── happy path ────────────────────────────────────────────────────────

class TestValidateDraftHappyPath:
    def test_valid_report_passes(self, neolyst_client, valid_report):
        """完整合法 draft 通过校验，返回 {report_id, version_no}。"""
        from skills.neolyst.scripts.validators import validate_draft

        result = validate_draft(
            neolyst_client,
            valid_report["report_id"],
            valid_report["version_no"],
        )
        assert result["report_id"] == valid_report["report_id"]
        assert result["version_no"] == valid_report["version_no"]


# ── field errors ─────────────────────────────────────────────────────

class TestValidateDraftFieldErrors:
    def test_missing_investment_thesis_fails(self, neolyst_client, test_coverage_id, tmp_path):
        """investment_thesis 为 None 时校验失败，错误含"投资论点"。"""
        from skills.neolyst.scripts.validators import validate_draft

        result = _save_draft(neolyst_client, tmp_path, {
            "investment_thesis": None,
            "coverage_id": test_coverage_id,
        })
        try:
            with pytest.raises(ValueError, match="投资论点"):
                validate_draft(neolyst_client, result["report_id"], result["version_no"])
        finally:
            _cleanup(neolyst_client, result["report_id"])

    def test_missing_contact_person_fails(self, neolyst_client, test_coverage_id, tmp_path):
        """contact_person 为 None 时校验失败，错误含"联系人"。"""
        from skills.neolyst.scripts.validators import validate_draft

        result = _save_draft(neolyst_client, tmp_path, {
            "contact_person": None,
            "coverage_id": test_coverage_id,
        })
        try:
            with pytest.raises(ValueError, match="联系人"):
                validate_draft(neolyst_client, result["report_id"], result["version_no"])
        finally:
            _cleanup(neolyst_client, result["report_id"])

    def test_missing_report_language_fails(self, neolyst_client, test_coverage_id, tmp_path):
        """report_language 为 None 时校验失败，错误含"报告语言"。"""
        from skills.neolyst.scripts.validators import validate_draft

        result = _save_draft(neolyst_client, tmp_path, {
            "report_language": None,
            "coverage_id": test_coverage_id,
        })
        try:
            with pytest.raises(ValueError, match="报告语言"):
                validate_draft(neolyst_client, result["report_id"], result["version_no"])
        finally:
            _cleanup(neolyst_client, result["report_id"])


# ── analyst errors ────────────────────────────────────────────────────

class TestValidateDraftAnalystErrors:
    def test_contact_person_not_in_analysts_fails(self, neolyst_client, test_coverage_id, tmp_path):
        """contact_person 不在 analysts 列表中时校验失败。"""
        from skills.neolyst.scripts.validators import validate_draft

        result = _save_draft(neolyst_client, tmp_path, {
            "contact_person": "nobody@example.com",
            "coverage_id": test_coverage_id,
        })
        try:
            with pytest.raises(ValueError, match="contact_person"):
                validate_draft(neolyst_client, result["report_id"], result["version_no"])
        finally:
            _cleanup(neolyst_client, result["report_id"])


# ── coverage errors ───────────────────────────────────────────────────

class TestValidateDraftCoverageErrors:
    def test_company_without_coverage_id_fails(self, neolyst_client, tmp_path):
        """company 类型不填 coverage_id 时校验失败，错误含"coverage_id"。"""
        from skills.neolyst.scripts.validators import validate_draft

        result = _save_draft(neolyst_client, tmp_path, {"coverage_id": None})
        try:
            with pytest.raises(ValueError, match="coverage_id"):
                validate_draft(neolyst_client, result["report_id"], result["version_no"])
        finally:
            _cleanup(neolyst_client, result["report_id"])


# ── version / file errors ─────────────────────────────────────────────

class TestValidateDraftVersionErrors:
    def test_nonexistent_version_fails(self, neolyst_client, valid_report):
        """传入不存在的 version_no=999 时校验失败，错误含"版本"。"""
        from skills.neolyst.scripts.validators import validate_draft

        with pytest.raises(ValueError, match="版本"):
            validate_draft(neolyst_client, valid_report["report_id"], 999)

    def test_missing_pdf_file_fails(self, neolyst_client, test_coverage_id, tmp_path):
        """pdf_file 未上传（pdf_file_path 为 None）时校验失败，错误含"PDF"。"""
        from skills.neolyst.scripts import draft_report
        from skills.neolyst.scripts.validators import validate_draft

        word = tmp_path / "report.docx"
        word.write_bytes(b"fake docx")
        result = draft_report.save_draft_report(neolyst_client, {
            "report_id": None,
            "title": "PDF Missing Test",
            "report_type": "company",
            "report_language": "zh",
            "investment_thesis": "test",
            "contact_person": TEST_ANALYST,
            "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
            "coverage_id": test_coverage_id,
            "ticker": None,
            "sector_id": None,
            "region_code": None,
            "rating": None,
            "target_price": None,
            "report_file": str(word),
            "pdf_file": None,       # ← 无 PDF
            "model_file": None,
        })
        try:
            with pytest.raises(ValueError, match="PDF"):
                validate_draft(neolyst_client, result["report_id"], result["version_no"])
        finally:
            _cleanup(neolyst_client, result["report_id"])


# ── status error ──────────────────────────────────────────────────────

class TestValidateDraftStatusErrors:
    def test_nonexistent_report_raises(self, neolyst_client):
        """不存在的 report_id 直接抛出 ValueError（不收集到 errors 列表中）。"""
        from skills.neolyst.scripts.validators import validate_draft

        with pytest.raises(ValueError, match="报告不存在"):
            validate_draft(neolyst_client, str(uuid.uuid4()), 1)
```

- [ ] **Step 2: 创建 test_submit_report.py**

```python
"""
test_submit_report.py — submit_report 集成测试（5 个）。
"""
import uuid
from pathlib import Path

import pytest

TEST_ANALYST = "yangxue@opendelp.com"


def _make_files(directory: Path) -> tuple[str, str]:
    word = directory / "report.docx"
    pdf = directory / "report.pdf"
    word.write_bytes(b"fake docx")
    pdf.write_bytes(b"fake pdf")
    return str(word), str(pdf)


@pytest.fixture(scope="module")
def submit_coverage_id(neolyst_client):
    from skills.neolyst.scripts import coverage as cov

    _suffix = uuid.uuid4().hex[:6].upper()
    sector_resp = neolyst_client.table("sector").select("id").eq("is_active", True).limit(1).execute()
    sector_id = sector_resp.data[0]["id"]

    cov_id = cov.create_coverage(
        neolyst_client,
        ticker=f"SUB{_suffix}",
        english_name=f"Submit Test Co {_suffix}",
        sector_id=sector_id,
        isin=f"HK{_suffix}{'0' * (10 - len(_suffix))}",
        country_of_domicile="Hong Kong",
        analysts=[{"analyst_email": TEST_ANALYST, "author_order": 1}],
    )
    yield cov_id
    neolyst_client.table("coverage").delete().eq("id", cov_id).execute()


@pytest.fixture(scope="module")
def submitted_report(neolyst_client, submit_coverage_id, tmp_path_factory):
    """首次提交合法报告，模块结束后清理。"""
    from skills.neolyst.scripts import draft_report, submit_report as sr

    d = tmp_path_factory.mktemp("submit_test")
    word_path, pdf_path = _make_files(d)
    draft = draft_report.save_draft_report(neolyst_client, {
        "report_id": None,
        "title": "Submit Test Report",
        "report_type": "company",
        "report_language": "en",
        "investment_thesis": "Test investment thesis",
        "contact_person": TEST_ANALYST,
        "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
        "ticker": "SUBTEST",
        "coverage_id": submit_coverage_id,
        "sector_id": None,
        "region_code": None,
        "rating": "OUTPERFORM",
        "target_price": 100.0,
        "report_file": word_path,
        "pdf_file": pdf_path,
        "model_file": None,
    })
    result = sr.submit_report(neolyst_client, draft["report_id"], draft["version_no"])
    yield result
    neolyst_client.table("report").delete().eq("id", result["report_id"]).execute()


class TestSubmitReport:
    def test_returns_submitted_status(self, submitted_report):
        """submit_report 返回 status == 'submitted'。"""
        assert submitted_report["status"] == "submitted"

    def test_returns_report_id_and_version(self, submitted_report):
        """返回 report_id（合法 UUID）和 version_no == 1。"""
        uuid.UUID(submitted_report["report_id"])
        assert submitted_report["version_no"] == 1

    def test_report_status_updated_in_db(self, neolyst_client, submitted_report):
        """report 表中 status 更新为 submitted。"""
        resp = (
            neolyst_client.table("report")
            .select("status")
            .eq("id", submitted_report["report_id"])
            .execute()
        )
        assert resp.data[0]["status"] == "submitted"

    def test_status_log_created(self, neolyst_client, submitted_report):
        """report_status_log 中有从 draft→submitted 的记录，action_by_name 为邮箱。"""
        resp = (
            neolyst_client.table("report_status_log")
            .select("*")
            .eq("report_id", submitted_report["report_id"])
            .execute()
        )
        assert resp.data
        log = resp.data[0]
        assert log["from_status"] == "draft"
        assert log["to_status"] == "submitted"
        assert log["version_no"] == 1
        assert "@" in (log["action_by_name"] or "")

    def test_submit_already_submitted_raises(self, neolyst_client, submitted_report):
        """对已 submitted 的报告再次调用 submit_report 抛出 ValueError。"""
        from skills.neolyst.scripts import submit_report as sr

        with pytest.raises(ValueError):
            sr.submit_report(
                neolyst_client,
                submitted_report["report_id"],
                submitted_report["version_no"],
            )
```

- [ ] **Step 3: 运行 validators 测试**

```bash
cd /mnt/c/_code/neoskills
NEOLYST_URL=http://127.0.0.1:54321 uv run --with pytest pytest skills/neolyst/tests/test_validators.py -v
```

Expected: 11 tests PASSED

- [ ] **Step 4: 运行 submit_report 测试**

```bash
NEOLYST_URL=http://127.0.0.1:54321 uv run --with pytest pytest skills/neolyst/tests/test_submit_report.py -v
```

Expected: 5 tests PASSED

- [ ] **Step 5: 全量测试**

```bash
NEOLYST_URL=http://127.0.0.1:54321 uv run --with pytest pytest skills/neolyst/tests/ -v
```

Expected: 全部通过（含 iter1~4 的 39 个，合计 55 个）

- [ ] **Step 6: Commit**

```bash
git add \
    supabase/migrations/20260410000100_080_submit_report_function.sql \
    skills/neolyst/scripts/validators.py \
    skills/neolyst/scripts/submit_report.py \
    skills/neolyst/tests/test_validators.py \
    skills/neolyst/tests/test_submit_report.py
git commit -m "feat: add validators and submit_report with submit_report RPC"
```

---

## Task 5: 更新文档和路线图

**Files:**
- Modify: `skills/neolyst/SKILL.md`
- Modify: `docs/skills_neolyst_design.md`
- Modify: `plans/2026-04-07-neolyst-skill-roadmap.md`

- [ ] **Step 1: 更新 SKILL.md**

将 `### 8. validators 🔲 待实现` 改为 `### 8. validators ✅ 已实现`

将 `### 9. submit_report 🔲 待实现` 改为 `### 9. submit_report ✅ 已实现`

- [ ] **Step 2: 更新 docs/skills_neolyst_design.md**

在报告相关设计部分追加一段说明：

```
- submit_report 流程：Python 侧先调 validate_draft（全量收集校验错误），通过后调 Supabase submit_report RPC（原子更新 report.status + 插入 report_status_log）。action_by_name 字段存调用者邮箱（auth.jwt() ->> 'email'）。
```

- [ ] **Step 3: 标记 Iter 5 完成**

将 `plans/2026-04-07-neolyst-skill-roadmap.md` 中：

```
| Iter 5 | validators + submit | 未开始 | — |
```

改为：

```
| Iter 5 | validators + submit | 已完成 | [2026-04-10-neolyst-iter5.md](2026-04-10-neolyst-iter5.md) |
```

- [ ] **Step 4: Commit**

```bash
git add \
    skills/neolyst/SKILL.md \
    docs/skills_neolyst_design.md \
    plans/2026-04-07-neolyst-skill-roadmap.md \
    plans/2026-04-10-neolyst-iter5.md
git commit -m "docs: mark iter5 complete, update SKILL.md and design doc"
```

---

## 自检

- [ ] 迁移文件包含：`report_status_is_valid` 更新（加 rejected→submitted）、`report_update` policy 更新（using 加 rejected）、`rsl_insert` policy 更新（analyst 从 rejected 可提交）、`submit_report` RPC；grant 给 authenticated，无 SECURITY DEFINER
- [ ] `submit_report` RPC：仅允许 draft/rejected → submitted；写入 report_status_log；action_by_name 用邮箱
- [ ] `validate_draft`：全量收集错误（不 fail-fast）；company 必须 coverage_id；sector/region 有值时才验证；contact_person 大小写不敏感比较
- [ ] `submit_report.py`：先调 validate_draft，通过后调 RPC
- [ ] 11 个 validators 测试通过，5 个 submit_report 测试通过
- [ ] 全量 55 个测试通过
- [ ] SKILL.md validators 和 submit_report 标记为 ✅ 已实现
- [ ] roadmap Iter 5 标记已完成
