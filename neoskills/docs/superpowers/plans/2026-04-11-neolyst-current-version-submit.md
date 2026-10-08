# Neolyst 当前版本校验与提交接口收口 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `validate_draft` 和 `submit_report` 收口为只接收 `report_id`，统一以 `report.current_version_no` 作为当前版本的唯一事实源，并同步更新 RPC、测试与对外文档。

**Architecture:**
- `validate_draft` 继续保留在 Python 侧，只做 SELECT 校验；它先读取 `report.current_version_no`，再校验当前版本对应的 `report_version` 与提交前字段完整性。
- `submit_report` 的 Python 包装层只负责调用 RPC；新的 `public.submit_report(p_report_id uuid)` 在数据库侧读取 `current_version_no`，做最低一致性保护，并把真实版本号写入 `report_status_log`。
- 仓内本轮直接硬切换，不保留旧签名兼容层；历史 plan 文档和本轮 spec 文档保留原样，不回写历史记录。

**Tech Stack:** Python 3.12, supabase-py, PostgreSQL PL/pgSQL, pytest, Markdown, uv, Supabase CLI

---

## 文件结构

| 文件 | 操作 | 说明 |
|------|------|------|
| `skills/neolyst/scripts/validators.py` | 修改 | `validate_draft` 改为只接收 `report_id`，按 `current_version_no` 定位当前版本 |
| `skills/neolyst/tests/test_validators.py` | 修改 | 更新校验接口签名，并补 `current_version_no` 边界用例 |
| `supabase/migrations/20260411000100_100_submit_report_current_version.sql` | 新增 | 新建 migration，替换 `submit_report(uuid, integer)` 为 `submit_report(uuid)` |
| `skills/neolyst/scripts/submit_report.py` | 修改 | Python 包装层改为只传 `report_id`，移除自动预校验 |
| `skills/neolyst/tests/test_submit_report.py` | 修改 | 更新提交接口签名，并补当前版本不存在 / 为 0 的保护测试 |
| `skills/neolyst/SKILL.md` | 修改 | 通过 `skill-creator` 更新公开接口说明 |
| `skills/neolyst/references/interfaces.md` | 修改 | 回写对外接口签名 |
| `docs/skills_neolyst_design.md` | 修改 | 回写实现边界 |
| `docs/skills_neolyst_integration.md` | 修改 | 回写上层接入方式 |
| `docs/codex/neolyst_skill_design.md` | 修改 | 回写 codex 视角设计说明 |
| `docs/codex/neolyst_skill_integration.md` | 修改 | 回写 codex 视角接入说明 |
| `docs/glm/neolyst_skill_design.md` | 修改 | 回写 glm 视角设计说明 |
| `docs/glm/neolyst_skill_integration.md` | 修改 | 回写 glm 视角接入说明 |
| `docs/kimi/neolyst_skill_integration.md` | 修改 | 回写 kimi 视角接入说明 |

## 背景与约束

- 本轮实现必须严格遵守已批准 spec：`docs/superpowers/specs/2026-04-11-neolyst-validate-draft-current-version-design.md`
- `SKILL.md` 不允许手改，必须通过 `skill-creator` 更新
- Supabase schema 变更必须通过新增 migration 落地，不能回改既有 migration 文件
- 本地验证需要执行 `supabase db reset`，确保新 migration 被完整回放
- 历史文档 `plans/2026-04-10-neolyst-iter5.md` 和本轮 spec 属于历史记录，不做签名替换

## Task 1: 收口 `validate_draft` 到当前版本语义

**Files:**
- Modify: `skills/neolyst/tests/test_validators.py`
- Modify: `skills/neolyst/scripts/validators.py`

- [ ] **Step 1: 先把 `validate_draft` 的测试改成新签名，并补当前版本边界用例**

在 `skills/neolyst/tests/test_validators.py` 中做三类变更：

```diff
-        result = validate_draft(
-            neolyst_client,
-            valid_report["report_id"],
-            valid_report["version_no"],
-        )
+        result = validate_draft(
+            neolyst_client,
+            valid_report["report_id"],
+        )
```

```diff
-                validate_draft(neolyst_client, result["report_id"], result["version_no"])
+                validate_draft(neolyst_client, result["report_id"])
```

```python
    def test_current_version_zero_fails(self, neolyst_client, test_coverage_id, tmp_path):
        """current_version_no=0 时校验失败，错误含"当前没有可校验版本"。"""
        from skills.neolyst.scripts.validators import validate_draft

        result = _save_draft(neolyst_client, tmp_path, {"coverage_id": test_coverage_id})
        try:
            (
                neolyst_client.table("report")
                .update({"current_version_no": 0})
                .eq("id", result["report_id"])
                .execute()
            )
            with pytest.raises(ValueError, match="当前没有可校验版本"):
                validate_draft(neolyst_client, result["report_id"])
        finally:
            _cleanup(neolyst_client, result["report_id"])

    def test_current_version_missing_row_fails(self, neolyst_client, test_coverage_id, tmp_path):
        """current_version_no 指向不存在的 report_version 时校验失败。"""
        from skills.neolyst.scripts.validators import validate_draft

        result = _save_draft(neolyst_client, tmp_path, {"coverage_id": test_coverage_id})
        try:
            (
                neolyst_client.table("report")
                .update({"current_version_no": 999})
                .eq("id", result["report_id"])
                .execute()
            )
            with pytest.raises(ValueError, match=r"当前版本 v999 不存在"):
                validate_draft(neolyst_client, result["report_id"])
        finally:
            _cleanup(neolyst_client, result["report_id"])
```

- [ ] **Step 2: 运行 `validate_draft` 测试，确认它先失败**

Run:
```bash
uv run pytest skills/neolyst/tests/test_validators.py -q
```

Expected:
- 失败，且至少包含 `TypeError: validate_draft() missing 1 required positional argument: 'version_no'`

- [ ] **Step 3: 将 `validate_draft` 的实现改成只按 `report_id` 校验当前版本**

将 `skills/neolyst/scripts/validators.py` 的函数签名、`report` 查询字段、版本定位逻辑和返回值改成下面这样：

```python
from supabase import Client


def validate_draft(client: Client, report_id: str) -> dict:
    """
    校验 draft 报告当前版本是否满足提交条件。

    Args:
        client: 已认证的 Supabase client
        report_id: 报告 UUID 字符串

    Returns:
        dict: {"report_id": report_id, "version_no": current_version_no}

    Raises:
        ValueError: 校验失败，消息列出所有失败项，以"；"分隔
    """
    errors: list[str] = []

    report_resp = (
        client.table("report")
        .select(
            "id, status, current_version_no, title, report_type, report_language, "
            "investment_thesis, contact_person, coverage_id, sector_id, region_code"
        )
        .eq("id", report_id)
        .execute()
    )
    if not report_resp.data:
        raise ValueError(f"报告不存在: {report_id}")

    report = report_resp.data[0]
    report_type = report.get("report_type")
    current_version_no = report.get("current_version_no") or 0

    if report["status"] not in ("draft", "rejected"):
        errors.append(f"报告状态为 {report['status']}，仅 draft/rejected 可提交")

    version = None
    if current_version_no <= 0:
        errors.append("报告当前没有可校验版本")
    else:
        version_resp = (
            client.table("report_version")
            .select("word_file_path, pdf_file_path")
            .eq("report_id", report_id)
            .eq("version_no", current_version_no)
            .execute()
        )
        if not version_resp.data:
            errors.append(f"当前版本 v{current_version_no} 不存在")
        else:
            version = version_resp.data[0]

    if version:
        if not version.get("word_file_path"):
            errors.append("缺少 Word 文件路径（word_file_path）")
        if not version.get("pdf_file_path"):
            errors.append("缺少 PDF 文件路径（pdf_file_path）")

    # 保留现有 required_fields / report_analyst / analyst / coverage / sector / region 校验逻辑

    if errors:
        raise ValueError("校验失败：" + "；".join(errors))

    return {"report_id": report_id, "version_no": current_version_no}
```

同时更新文件顶部注释和 docstring，把“指定版本”全部改成“当前版本”。

- [ ] **Step 4: 再跑一遍 `validate_draft` 测试，确认新签名和边界都通过**

Run:
```bash
uv run pytest skills/neolyst/tests/test_validators.py -q
```

Expected:
- 通过，且输出中无 `FAIL` / `ERROR`

- [ ] **Step 5: 提交 `validate_draft` 收口改动**

Run:
```bash
git add skills/neolyst/scripts/validators.py skills/neolyst/tests/test_validators.py
git commit -m "refactor: validate current neolyst draft by report id"
```

Expected:
- 成功创建只包含 validator 改动的提交

## Task 2: 收口 `submit_report` RPC 与 Python 包装层

**Files:**
- Modify: `skills/neolyst/tests/test_submit_report.py`
- Create: `supabase/migrations/20260411000100_100_submit_report_current_version.sql`
- Modify: `skills/neolyst/scripts/submit_report.py`

- [ ] **Step 1: 先把 `submit_report` 测试改成新签名，并补服务端当前版本保护用例**

在 `skills/neolyst/tests/test_submit_report.py` 中先替换现有调用：

```diff
-    result = sr.submit_report(neolyst_client, draft["report_id"], draft["version_no"])
+    result = sr.submit_report(neolyst_client, draft["report_id"])
```

```diff
-            sr.submit_report(
-                neolyst_client,
-                submitted_report["report_id"],
-                submitted_report["version_no"],
-            )
+            sr.submit_report(
+                neolyst_client,
+                submitted_report["report_id"],
+            )
```

再追加两个测试：

```python
    def test_submit_without_current_version_raises(self, neolyst_client, submit_coverage_id, tmp_path):
        """current_version_no=0 时 submit_report 抛出 ValueError。"""
        from skills.neolyst.scripts import draft_report
        from skills.neolyst.scripts import submit_report as sr

        word_path, pdf_path = _make_files(tmp_path)
        draft = draft_report.save_draft_report(neolyst_client, {
            "report_id": None,
            "title": "Submit No Version",
            "report_type": "company",
            "report_language": "en",
            "investment_thesis": "Test investment thesis",
            "contact_person": TEST_ANALYST,
            "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
            "ticker": "SUBZERO",
            "coverage_id": submit_coverage_id,
            "sector_id": None,
            "region_code": None,
            "rating": "OUTPERFORM",
            "target_price": 100.0,
            "report_file": word_path,
            "pdf_file": pdf_path,
            "model_file": None,
        })
        try:
            (
                neolyst_client.table("report")
                .update({"current_version_no": 0})
                .eq("id", draft["report_id"])
                .execute()
            )
            with pytest.raises(ValueError, match="当前没有可提交版本"):
                sr.submit_report(neolyst_client, draft["report_id"])
        finally:
            neolyst_client.table("report").delete().eq("id", draft["report_id"]).execute()

    def test_submit_with_missing_current_version_row_raises(self, neolyst_client, submit_coverage_id, tmp_path):
        """current_version_no 指向不存在版本时 submit_report 抛出 ValueError。"""
        from skills.neolyst.scripts import draft_report
        from skills.neolyst.scripts import submit_report as sr

        word_path, pdf_path = _make_files(tmp_path)
        draft = draft_report.save_draft_report(neolyst_client, {
            "report_id": None,
            "title": "Submit Missing Version",
            "report_type": "company",
            "report_language": "en",
            "investment_thesis": "Test investment thesis",
            "contact_person": TEST_ANALYST,
            "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
            "ticker": "SUBMISS",
            "coverage_id": submit_coverage_id,
            "sector_id": None,
            "region_code": None,
            "rating": "OUTPERFORM",
            "target_price": 100.0,
            "report_file": word_path,
            "pdf_file": pdf_path,
            "model_file": None,
        })
        try:
            (
                neolyst_client.table("report")
                .update({"current_version_no": 999})
                .eq("id", draft["report_id"])
                .execute()
            )
            with pytest.raises(ValueError, match=r"当前版本 v999 不存在"):
                sr.submit_report(neolyst_client, draft["report_id"])
        finally:
            neolyst_client.table("report").delete().eq("id", draft["report_id"]).execute()
```

- [ ] **Step 2: 先跑 `submit_report` 测试，确认接口改动会让现状失败**

Run:
```bash
uv run pytest skills/neolyst/tests/test_submit_report.py -q
```

Expected:
- 失败，且至少包含 `TypeError: submit_report() missing 1 required positional argument: 'version_no'`

- [ ] **Step 3: 新增 migration，用 `current_version_no` 替换旧的 RPC 入参**

创建 `supabase/migrations/20260411000100_100_submit_report_current_version.sql`，内容写完整：

```sql
-- 20260411000100_100_submit_report_current_version.sql
-- submit_report 改为只接收 report_id，并在数据库侧读取 current_version_no

drop function if exists public.submit_report(uuid, integer);

create or replace function public.submit_report(
    p_report_id uuid
)
returns table(report_id uuid, version_no integer, status text)
language plpgsql
as $$
declare
    v_current_status     text;
    v_current_version_no integer;
    v_action_email       text;
begin
    select r.status, r.current_version_no
      into v_current_status, v_current_version_no
    from public.report r
    where r.id = p_report_id;

    if not found then
        raise exception '报告不存在: %', p_report_id;
    end if;

    if v_current_status not in ('draft', 'rejected') then
        raise exception '报告状态为 %，无法提交（仅 draft/rejected 可提交）', v_current_status;
    end if;

    if coalesce(v_current_version_no, 0) <= 0 then
        raise exception '报告当前没有可提交版本';
    end if;

    if not exists (
        select 1
        from public.report_version rv
        where rv.report_id = p_report_id
          and rv.version_no = v_current_version_no
    ) then
        raise exception '当前版本 v% 不存在', v_current_version_no;
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
        auth.uid(), v_action_email, v_current_version_no
    );

    return query
        select p_report_id, v_current_version_no, 'submitted'::text;
end;
$$;

comment on function public.submit_report(uuid) is
'将 draft/rejected 状态的报告当前版本提交为 submitted。数据库侧读取 report.current_version_no，
拒绝 current_version_no<=0 或当前版本缺失的报告，并将真实版本号写入 report_status_log。';

revoke execute on function public.submit_report(uuid) from public, anon;
grant execute on function public.submit_report(uuid) to authenticated;
```

- [ ] **Step 4: 更新 Python 包装层，移除 `version_no` 入参与自动预校验**

将 `skills/neolyst/scripts/submit_report.py` 改成下面这样：

```python
"""
submit_report.py — Neolyst 报告提交接口。

流程：
1. 调用 submit_report RPC
2. 返回 {report_id, version_no, status}

业务逻辑（当前版本定位、状态流转、日志写入）全部在 Supabase RPC 侧，本模块只做调用串联。
"""

from supabase import Client


def submit_report(client: Client, report_id: str) -> dict:
    """
    提交 draft/rejected 报告当前版本为 submitted 状态。

    Args:
        client: 已认证的 Supabase client
        report_id: 报告 UUID 字符串

    Returns:
        dict: {"report_id": str, "version_no": int, "status": "submitted"}

    Raises:
        ValueError: RPC 调用失败
    """
    try:
        resp = client.rpc("submit_report", {
            "p_report_id": report_id,
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

- [ ] **Step 5: 重置本地 Supabase，应用新 migration**

Run:
```bash
supabase db reset
```

Expected:
- 末尾输出 `Finished supabase db reset`
- 无 `ERROR`

- [ ] **Step 6: 再跑 `submit_report` 测试，确认新 RPC 契约与边界保护通过**

Run:
```bash
uv run pytest skills/neolyst/tests/test_submit_report.py -q
```

Expected:
- 通过，且输出中无 `FAIL` / `ERROR`

- [ ] **Step 7: 提交 `submit_report` 收口改动**

Run:
```bash
git add supabase/migrations/20260411000100_100_submit_report_current_version.sql skills/neolyst/scripts/submit_report.py skills/neolyst/tests/test_submit_report.py
git commit -m "refactor: submit current report version by report id"
```

Expected:
- 成功创建只包含 submit_report / migration 改动的提交

## Task 3: 同步对外文档和 Skill 接口说明

**Files:**
- Modify: `skills/neolyst/SKILL.md`
- Modify: `skills/neolyst/references/interfaces.md`
- Modify: `docs/skills_neolyst_design.md`
- Modify: `docs/skills_neolyst_integration.md`
- Modify: `docs/codex/neolyst_skill_design.md`
- Modify: `docs/codex/neolyst_skill_integration.md`
- Modify: `docs/glm/neolyst_skill_design.md`
- Modify: `docs/glm/neolyst_skill_integration.md`
- Modify: `docs/kimi/neolyst_skill_integration.md`

- [ ] **Step 1: 用 `skill-creator` 更新 `SKILL.md` 中的公开接口说明**

通过 `skill-creator` 将 `skills/neolyst/SKILL.md` 的第 8、9 节改成下面这组内容：

````md
### 8. validate_draft ✅ 已实现

校验当前 draft 的当前版本是否满足提交条件。全量收集所有错误后一次性抛出。

```python
from skills.neolyst.scripts.validators import validate_draft

result = validate_draft(client, report_id="uuid")
# 通过：返回 {"report_id": "uuid", "version_no": 1}
# 失败：抛出 ValueError（消息以"；"分隔所有失败项，足以让调用方据此补字段）
```

**校验内容：** report 存在且状态为 draft/rejected、`report.current_version_no` 大于 0、当前版本存在、word/pdf 文件路径非空、必填字段（title/report_type/report_language/investment_thesis/contact_person）、分析师列表非空且 contact_person 在内、每个分析师存在且 is_active、company 类型必须有 coverage_id 且存在、sector_id/region_code 有值时验证存在性。

### 9. submit_report ✅ 已实现

将当前 draft/rejected 版本提交为 `submitted` 状态。

```python
from skills.neolyst.scripts import submit_report

result = submit_report.submit_report(client, report_id="uuid")
# 返回：{"report_id": "uuid", "status": "submitted", "version_no": 1}
# 提交前如需完整字段校验，请先显式调用 validate_draft(client, report_id="uuid")
```
````

- [ ] **Step 2: 批量回写其余文档中的接口签名和行为说明**

将下列旧表述统一替换为新契约：

```diff
- validate_draft(report_id, version_no)
+ validate_draft(report_id)
```

```diff
- submit_report(report_id, version_no)
+ submit_report(report_id)
```

并统一补上这两条行为说明：

```md
- `validate_draft` 读取 `report.current_version_no`，只校验当前版本。
- `submit_report` 只接收 `report_id`，数据库 RPC 内部读取当前版本并返回真实 `version_no`。
```

在 integration 文档里把“提交前由上层流程调用 `validate_draft(report_id, version_no)`”改成：

```md
在人工确认提交前，根据 `report_id` 调用 `validate_draft(report_id)` 对当前版本执行提交前校验。
若确认提交，再调用 `submit_report(report_id)`；返回值中的 `version_no` 为实际提交版本。
```

- [ ] **Step 3: 用 grep 验证活动代码和活动文档里已不存在旧签名**

Run:
```bash
rg -n "validate_draft\\(.*version_no|submit_report\\(.*version_no" \
  skills/neolyst/SKILL.md \
  skills/neolyst/references/interfaces.md \
  docs/skills_neolyst_design.md \
  docs/skills_neolyst_integration.md \
  docs/codex/neolyst_skill_design.md \
  docs/codex/neolyst_skill_integration.md \
  docs/glm/neolyst_skill_design.md \
  docs/glm/neolyst_skill_integration.md \
  docs/kimi/neolyst_skill_integration.md \
  skills/neolyst/scripts/validators.py \
  skills/neolyst/scripts/submit_report.py \
  skills/neolyst/tests/test_validators.py \
  skills/neolyst/tests/test_submit_report.py
```

Expected:
- 无输出

- [ ] **Step 4: 提交文档与 Skill 说明改动**

Run:
```bash
git add skills/neolyst/SKILL.md skills/neolyst/references/interfaces.md docs/skills_neolyst_design.md docs/skills_neolyst_integration.md docs/codex/neolyst_skill_design.md docs/codex/neolyst_skill_integration.md docs/glm/neolyst_skill_design.md docs/glm/neolyst_skill_integration.md docs/kimi/neolyst_skill_integration.md
git commit -m "docs: align neolyst current-version contract"
```

Expected:
- 成功创建只包含文档改动的提交

## Task 4: 做最终验证，确认硬切换没有漏点

**Files:**
- Modify: `docs/superpowers/plans/2026-04-11-neolyst-current-version-submit.md`（执行时勾选完成项）

- [ ] **Step 1: 重新回放 migration，再跑当前功能相关测试**

Run:
```bash
supabase db reset
uv run pytest skills/neolyst/tests/test_validators.py skills/neolyst/tests/test_submit_report.py -q
```

Expected:
- `supabase db reset` 成功结束，无 `ERROR`
- 两个测试文件全部通过，无 `FAIL` / `ERROR`

- [ ] **Step 2: 跑一遍 `neolyst` 全量测试，确认没有被这次硬切换误伤**

Run:
```bash
uv run pytest skills/neolyst/tests -q
```

Expected:
- 全量通过

- [ ] **Step 3: 做 repo 级签名残留扫描，只允许历史计划和本轮 spec 继续保留旧写法**

Run:
```bash
rg -n "validate_draft\\(.*version_no|submit_report\\(.*version_no" docs skills plans | sort
```

Expected:
- 只剩历史文档或设计记录中的旧签名引用
- 允许保留：
  - `docs/superpowers/specs/2026-04-11-neolyst-validate-draft-current-version-design.md`
  - `plans/2026-04-10-neolyst-iter5.md`

## 完成标准

- [ ] `validate_draft` 已改为 `validate_draft(client, report_id)`，并返回真实当前版本号
- [ ] `submit_report` 已改为 `submit_report(client, report_id)`，Python 侧不再传 `version_no`
- [ ] Supabase 侧已存在新的 `submit_report(uuid)` migration，最低一致性保护已生效
- [ ] `skills/neolyst/tests/test_validators.py` 和 `skills/neolyst/tests/test_submit_report.py` 已覆盖 `current_version_no=0` 与“当前版本缺失”场景
- [ ] 对外说明文档、Skill 文档和接口参考已完成硬切换
- [ ] `uv run pytest skills/neolyst/tests -q` 通过
