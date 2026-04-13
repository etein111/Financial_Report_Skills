# submit_report 字段完整性校验下沉 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将报告提交前的字段完整性校验下沉到 DB 侧 `validate_report` RPC，使 `submit_report` 成为数据一致性的最终守门员，并以同名 Python 接口对外暴露。

**Architecture:** 新增 `validate_report` RPC（全量收集错误后一次性 RAISE），`submit_report` RPC 内部调用它；Python 层 `validate_draft` 删除，替换为调用 RPC 的 `validate_report` 函数；SKILL.md / interfaces.md 随之更新。

**Tech Stack:** PostgreSQL / PL/pgSQL / Supabase-py / pytest

---

### Task 1: 新增 validate_report RPC 迁移文件

**Files:**
- Create: `supabase/migrations/20260413000300_112_validate_report_rpc.sql`

- [ ] **Step 1: 写迁移 SQL**

```sql
-- 20260413000300_112_validate_report_rpc.sql
-- 新增 validate_report RPC：全量收集报告字段完整性错误，独立可调

create or replace function public.validate_report(p_report_id uuid)
returns void
language plpgsql
as $$
declare
    v_errors         text[] := '{}';
    v_report         record;
    v_version        record;
    v_analyst_count  integer;
    v_bad_analyst    text;
begin
    -- 1. 报告存在（立即 RAISE，不入数组）
    select r.status, r.current_version_no,
           r.title, r.report_type, r.report_language,
           r.investment_thesis, r.contact_person,
           r.coverage_id, r.sector_id, r.region_code
      into v_report
      from public.report r
     where r.id = p_report_id;

    if not found then
        raise exception '报告不存在: %', p_report_id;
    end if;

    -- 2. 状态校验
    if v_report.status not in ('draft', 'rejected') then
        v_errors := v_errors || format(
            '报告状态为 %s，仅 draft/rejected 可提交', v_report.status);
    end if;

    -- 3. 必填字段
    if v_report.title is null or v_report.title = '' then
        v_errors := v_errors || '缺少必填字段：标题（title）';
    end if;
    if v_report.report_type is null or v_report.report_type = '' then
        v_errors := v_errors || '缺少必填字段：报告类型（report_type）';
    end if;
    if v_report.report_language is null or v_report.report_language = '' then
        v_errors := v_errors || '缺少必填字段：报告语言（report_language）';
    end if;
    if v_report.investment_thesis is null or v_report.investment_thesis = '' then
        v_errors := v_errors || '缺少必填字段：投资论点（investment_thesis）';
    end if;
    if v_report.contact_person is null or v_report.contact_person = '' then
        v_errors := v_errors || '缺少必填字段：联系人（contact_person）';
    end if;

    -- 4. 版本存在性
    if coalesce(v_report.current_version_no, 0) <= 0 then
        v_errors := v_errors || '报告当前没有可校验版本';
    else
        select rv.word_file_path, rv.pdf_file_path
          into v_version
          from public.report_version rv
         where rv.report_id = p_report_id
           and rv.version_no = v_report.current_version_no;

        if not found then
            v_errors := v_errors || format('当前版本 v%s 不存在', v_report.current_version_no);
        else
            -- 5. 文件路径
            if v_version.word_file_path is null or v_version.word_file_path = '' then
                v_errors := v_errors || '缺少 Word 文件路径（word_file_path）';
            end if;
            if v_version.pdf_file_path is null or v_version.pdf_file_path = '' then
                v_errors := v_errors || '缺少 PDF 文件路径（pdf_file_path）';
            end if;
        end if;
    end if;

    -- 6. 分析师列表非空
    select count(*)
      into v_analyst_count
      from public.report_analyst
     where report_id = p_report_id;

    if v_analyst_count = 0 then
        v_errors := v_errors || '报告没有分析师（report_analyst 为空）';
    else
        -- contact_person 在分析师列表中（大小写不敏感）
        if v_report.contact_person is not null
           and not exists (
               select 1
                 from public.report_analyst
                where report_id = p_report_id
                  and lower(analyst_email) = lower(v_report.contact_person)
           ) then
            v_errors := v_errors || format(
                'contact_person（%s）不在本报告分析师列表中', v_report.contact_person);
        end if;

        -- 找出第一个问题分析师（不存在或已停用）
        select ra.analyst_email
          into v_bad_analyst
          from public.report_analyst ra
          left join public.analyst a on a.email = ra.analyst_email
         where ra.report_id = p_report_id
           and (a.email is null or not a.is_active)
         limit 1;

        if found then
            if exists (
                select 1 from public.analyst
                 where email = v_bad_analyst and not is_active
            ) then
                v_errors := v_errors || format('分析师已停用：%s', v_bad_analyst);
            else
                v_errors := v_errors || format('分析师不存在：%s', v_bad_analyst);
            end if;
        end if;
    end if;

    -- 7. company / company_flash：coverage_id 必填且存在
    if v_report.report_type in ('company', 'company_flash') then
        if v_report.coverage_id is null then
            v_errors := v_errors || format(
                '公司类报告（%s）必须关联 coverage_id', v_report.report_type);
        elsif not exists (
            select 1 from public.coverage where id = v_report.coverage_id
        ) then
            v_errors := v_errors || format('coverage 不存在：%s', v_report.coverage_id);
        end if;
    end if;

    -- 8. sector_id 有值时验证存在性
    if v_report.sector_id is not null
       and not exists (select 1 from public.sector where id = v_report.sector_id) then
        v_errors := v_errors || format('sector 不存在：%s', v_report.sector_id);
    end if;

    -- 9. region_code 有值时验证存在性
    if v_report.region_code is not null
       and not exists (select 1 from public.region where code = v_report.region_code) then
        v_errors := v_errors || format('region 不存在：%s', v_report.region_code);
    end if;

    -- 全部错误一次抛出
    if array_length(v_errors, 1) > 0 then
        raise exception '校验失败：%', array_to_string(v_errors, '；');
    end if;
end;
$$;

comment on function public.validate_report(uuid) is
'全量校验报告字段完整性（必填字段、文件路径、分析师、coverage 等）。
所有错误收集后一次性 RAISE，消息以"；"分隔。独立可调，也被 submit_report 内部调用。';

revoke execute on function public.validate_report(uuid) from public, anon;
grant execute on function public.validate_report(uuid) to authenticated;
```

- [ ] **Step 2: 应用迁移**

```bash
cd /mnt/c/_code/neoskills && npx supabase db reset
```

Expected: 输出迁移成功，无报错。

---

### Task 2: 更新 test_validators.py（RED → GREEN）

**Files:**
- Modify: `skills/neolyst/tests/test_validators.py`

- [ ] **Step 1: 将所有 validate_draft 替换为 validate_report**

文件中每处 `validate_draft` 替换为 `validate_report`（共 12 处：1 处 import + 11 处调用）：

```python
# 替换前
from skills.neolyst.scripts.validators import validate_draft
# ...
v = validate_draft(neolyst_client, result["report_id"])

# 替换后
from skills.neolyst.scripts.validators import validate_report
# ...
v = validate_report(neolyst_client, result["report_id"])
```

所有 `validate_draft(` 改为 `validate_report(`，断言内容不变。

- [ ] **Step 2: 运行验证失败（RED）**

```bash
cd /mnt/c/_code/neoskills && uv run pytest skills/neolyst/tests/test_validators.py -v 2>&1 | head -20
```

Expected: FAIL，错误为 `ImportError: cannot import name 'validate_report' from 'skills.neolyst.scripts.validators'`

---

### Task 3: 重写 validators.py

**Files:**
- Modify: `skills/neolyst/scripts/validators.py`

- [ ] **Step 1: 用以下内容完整替换 validators.py**

```python
"""
validators.py — Neolyst 报告提交前校验。

校验逻辑的单一事实源在 DB 侧（validate_report RPC）。
Python 层只封装 RPC 调用，返回标准化结果。
"""

from supabase import Client

from . import rpc


def validate_report(client: Client, report_id: str) -> dict:
    """
    调用 validate_report RPC，校验报告当前版本是否满足提交条件。
    校验逻辑在 DB 侧，此函数只封装调用。

    Args:
        client: 已认证的 Supabase client
        report_id: 报告 UUID 字符串

    Returns:
        dict: {"report_id": report_id, "version_no": int}（校验通过时）

    Raises:
        ValueError: 校验失败，消息列出所有失败项，以"；"分隔
    """
    resp = (
        client.table("report")
        .select("current_version_no")
        .eq("id", report_id)
        .execute()
    )
    if not resp.data:
        raise ValueError(f"报告不存在: {report_id}")
    version_no = resp.data[0]["current_version_no"] or 0

    rpc.call_rpc(client, "validate_report", {"p_report_id": report_id})
    return {"report_id": report_id, "version_no": version_no}
```

- [ ] **Step 2: 运行 test_validators.py 验证全部通过（GREEN）**

```bash
cd /mnt/c/_code/neoskills && uv run pytest skills/neolyst/tests/test_validators.py -v
```

Expected: 11 passed。

- [ ] **Step 3: Commit**

```bash
cd /mnt/c/_code/neoskills
git add supabase/migrations/20260413000300_112_validate_report_rpc.sql \
        skills/neolyst/scripts/validators.py \
        skills/neolyst/tests/test_validators.py
git commit -m "feat(neolyst): 新增 validate_report RPC，Python 层委托调用"
```

---

### Task 4: 新增 test_submit_report.py 守门员测试（RED）

**Files:**
- Modify: `skills/neolyst/tests/test_submit_report.py`

- [ ] **Step 1: 在 TestSubmitReport 类末尾追加两个测试方法**

在文件末尾 `test_submit_with_missing_current_version_row_raises` 方法之后，追加以下两个方法（保持缩进在 `TestSubmitReport` 类内）：

```python
    def test_submit_missing_investment_thesis_raises(
        self, neolyst_client, submit_coverage_id, tmp_path
    ):
        """investment_thesis 置 NULL 后直接 submit_report 被 RPC 守门员拦截。"""
        from skills.neolyst.scripts import draft_report
        from skills.neolyst.scripts import submit_report as sr

        word_path, pdf_path = _make_files(tmp_path)
        draft = draft_report.save_draft_report(neolyst_client, {
            "report_id": None,
            "title": "Validate Gate Test",
            "report_type": "company",
            "report_language": "en",
            "investment_thesis": "initial thesis",
            "contact_person": TEST_ANALYST,
            "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
            "ticker": "VGATE",
            "coverage_id": submit_coverage_id,
            "sector_id": None,
            "region_code": None,
            "rating": None,
            "target_price": None,
            "report_file": word_path,
            "pdf_file": pdf_path,
            "model_file": None,
        })
        try:
            neolyst_client.table("report").update(
                {"investment_thesis": None}
            ).eq("id", draft["report_id"]).execute()
            with pytest.raises(ValueError, match="投资论点"):
                sr.submit_report(neolyst_client, draft["report_id"])
        finally:
            neolyst_client.table("report").delete().eq(
                "id", draft["report_id"]
            ).execute()

    def test_submit_company_without_coverage_raises(
        self, neolyst_client, submit_coverage_id, tmp_path
    ):
        """company 报告 coverage_id 置 NULL 后直接 submit_report 被 RPC 守门员拦截。"""
        from skills.neolyst.scripts import draft_report
        from skills.neolyst.scripts import submit_report as sr

        word_path, pdf_path = _make_files(tmp_path)
        draft = draft_report.save_draft_report(neolyst_client, {
            "report_id": None,
            "title": "Coverage Gate Test",
            "report_type": "company",
            "report_language": "en",
            "investment_thesis": "test thesis",
            "contact_person": TEST_ANALYST,
            "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
            "ticker": "CGATE",
            "coverage_id": submit_coverage_id,
            "sector_id": None,
            "region_code": None,
            "rating": None,
            "target_price": None,
            "report_file": word_path,
            "pdf_file": pdf_path,
            "model_file": None,
        })
        try:
            neolyst_client.table("report").update(
                {"coverage_id": None}
            ).eq("id", draft["report_id"]).execute()
            with pytest.raises(ValueError, match="coverage_id"):
                sr.submit_report(neolyst_client, draft["report_id"])
        finally:
            neolyst_client.table("report").delete().eq(
                "id", draft["report_id"]
            ).execute()
```

- [ ] **Step 2: 运行验证失败（RED）**

```bash
cd /mnt/c/_code/neoskills && uv run pytest skills/neolyst/tests/test_submit_report.py::TestSubmitReport::test_submit_missing_investment_thesis_raises skills/neolyst/tests/test_submit_report.py::TestSubmitReport::test_submit_company_without_coverage_raises -v
```

Expected: FAIL — `submit_report` 不抛出 ValueError（RPC 尚未校验字段）。

---

### Task 5: 新增 submit_report 更新迁移 + 应用（GREEN）

**Files:**
- Create: `supabase/migrations/20260413000400_113_submit_report_call_validate.sql`

- [ ] **Step 1: 写迁移 SQL**

```sql
-- 20260413000400_113_submit_report_call_validate.sql
-- submit_report 在状态校验后调用 validate_report，实现字段完整性守门

drop function if exists public.submit_report(uuid);

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
        raise exception '报告状态为 %，无法提交（仅 draft/rejected 可提交）',
            v_current_status;
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

    -- 字段完整性守门：调用 validate_report，校验失败时异常向上传播
    perform public.validate_report(p_report_id);

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
'将 draft/rejected 状态的报告当前版本提交为 submitted。
状态/版本快速失败校验后调用 validate_report 做字段完整性守门，
再原子更新 report.status 并写入 report_status_log。';

revoke execute on function public.submit_report(uuid) from public, anon;
grant execute on function public.submit_report(uuid) to authenticated;
```

- [ ] **Step 2: 应用迁移**

```bash
cd /mnt/c/_code/neoskills && npx supabase db reset
```

Expected: 输出迁移成功，无报错。

- [ ] **Step 3: 运行新增守门员测试（GREEN）**

```bash
cd /mnt/c/_code/neoskills && uv run pytest skills/neolyst/tests/test_submit_report.py::TestSubmitReport::test_submit_missing_investment_thesis_raises skills/neolyst/tests/test_submit_report.py::TestSubmitReport::test_submit_company_without_coverage_raises -v
```

Expected: 2 passed。

- [ ] **Step 4: 运行全部 submit 测试确认无回归**

```bash
cd /mnt/c/_code/neoskills && uv run pytest skills/neolyst/tests/test_submit_report.py -v
```

Expected: 9 passed（原 7 + 新增 2）。

- [ ] **Step 5: Commit**

```bash
cd /mnt/c/_code/neoskills
git add supabase/migrations/20260413000400_113_submit_report_call_validate.sql \
        skills/neolyst/tests/test_submit_report.py
git commit -m "feat(neolyst): submit_report 调用 validate_report 实现字段守门"
```

---

### Task 6: 更新 SKILL.md 和 interfaces.md

**Files:**
- Modify: `skills/neolyst/SKILL.md`
- Modify: `skills/neolyst/references/interfaces.md`

- [ ] **Step 1: 更新 SKILL.md 接口表第 8 条**

将：
```markdown
| 8 | `validate_draft(client, report_id)` | `validators` | 校验当前 draft 版本是否满足提交条件，收集全部错误 |
```
替换为：
```markdown
| 8 | `validate_report(client, report_id)` | `validators` | 调用 DB 侧 RPC 校验报告当前版本是否满足提交条件，全量收集错误 |
```

- [ ] **Step 2: 更新 SKILL.md 业务约束第 3 条**

将：
```markdown
- `submit_report`：只提交 `report.current_version_no` 指向的当前版本；如需完整字段校验，调用方先显式调用 `validate_draft`
```
替换为：
```markdown
- `submit_report`：只提交 `report.current_version_no` 指向的当前版本；RPC 内部已调用 `validate_report` 做字段守门，如需提前获取友好的全量错误展示，调用方先显式调用 `validate_report`
```

- [ ] **Step 3: 替换 interfaces.md §8（validate_draft → validate_report）**

将整个 `## 8. validate_draft` 节替换为：

```markdown
## 8. validate_report

调用 DB 侧 `validate_report` RPC，校验报告当前版本是否满足提交条件。全量收集所有错误后一次性返回。

```python
from skills.neolyst.scripts.validators import validate_report

result = validate_report(client, report_id="uuid")
# 通过：返回 {"report_id": "uuid", "version_no": 1}
# 失败：抛出 ValueError（消息以"；"分隔所有失败项）
```

只负责校验，不自动补字段、不自动重试、不自动保存 draft。

当前版本由 `report.current_version_no` 决定。

校验范围：
- report 存在且状态为 draft/rejected
- `report.current_version_no` 大于 0，且当前版本存在
- word/pdf 文件路径非空
- 必填字段：title / report_type / report_language / investment_thesis / contact_person
- 分析师列表非空，且 contact_person 在分析师列表中（大小写不敏感）
- 每个分析师存在且 is_active
- company / company_flash 类型：coverage_id 必填且存在
- sector_id / region_code 有值时验证存在性
```

- [ ] **Step 4: 更新 interfaces.md §9 submit_report 说明**

在 §9 的示例代码块下方，将：
```markdown
# 提交前如需完整字段校验，请先显式调用 validate_draft(client, report_id="uuid")
```
替换为：
```markdown
# RPC 内部调用 validate_report 做字段守门，字段不完整时抛出 ValueError
# 如需提前获取全量错误展示，先显式调用 validate_report(client, report_id="uuid")
```

- [ ] **Step 5: 更新 interfaces.md 错误处理策略节标题**

将：
```markdown
### validate_draft 校验失败
```
替换为：
```markdown
### validate_report 校验失败
```

- [ ] **Step 6: Commit**

```bash
cd /mnt/c/_code/neoskills
git add skills/neolyst/SKILL.md \
        skills/neolyst/references/interfaces.md
git commit -m "docs(neolyst): validate_draft → validate_report，更新接口说明"
```

---

### Task 7: 运行全量测试确认无回归

- [ ] **Step 1: 运行全部 neolyst 测试**

```bash
cd /mnt/c/_code/neoskills && uv run pytest skills/neolyst/tests/ -v
```

Expected: 全部通过，无 FAIL / ERROR。

- [ ] **Step 2: 若有失败，查看错误并修复**

常见原因：
- `validate_draft` 残留引用：全局搜索 `validate_draft`，替换为 `validate_report`
- RPC 权限问题：确认迁移已完整应用（`npx supabase db reset`）
- 测试 fixture 数据问题：确认 `test_config.json` 中的 analyst 邮箱在 DB 中存在且 `is_active = true`
