# Neolyst Iter 4: draft_report 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 `save_draft_report`，包含 Supabase 侧两个 RPC 和 Python 侧 `draft_report.py`，支持新建或追加版本保存机器处理后的 draft 报告；同时更新 SKILL.md。

**Architecture:**
- **Supabase 侧**：新增迁移文件，补充 `ra_delete` policy（analyst 可删除自己报告的 `report_analyst`），定义两个 RPC：`init_draft_report`（创建/更新 report + 全量替换 report_analyst）和 `commit_draft_version`（插入 report_version + 更新 current_version_no）。
- **`draft_report.py`**：Python 侧串联两个 RPC，中间做文件上传。流程：`init_draft_report` → 上传文件到 `reports/{report_id}/v{version_no}/{filename}` → `commit_draft_version`。此顺序确保 report 已存在于 DB 后再上传，analyst 的 Storage 权限不被拦截。
- **集成测试**：直接打 local Supabase，复用 `neolyst_client` fixture，module 级 teardown 清理数据。

**Tech Stack:** Python 3.12+, supabase-py, uuid, pytest, tmp_path_factory

**已确认的设计决策：**
- Python 用 `uuid.uuid4()` 生成 `report_id`（首次 save 时传入 None）
- 流程分两步：先 `init_draft_report`（建 report），再上传文件，再 `commit_draft_version`（建 version）
- 报告文件路径：`reports/{report_id}/v{version_no}/{原始文件名}`，版本间互不覆盖
- `report_analyst` 全量替换（ra_delete policy + INSERT，无需 SECURITY DEFINER）
- `snapshot_json` = draft 入参去掉本地路径字段（`report_file`/`pdf_file`/`model_file`）+ 加上 storage 路径

---

## 文件结构

| 文件 | 操作 | 说明 |
|------|------|------|
| `supabase/migrations/20260409000640_070_draft_report_functions.sql` | 新建 | ra_delete policy + `init_draft_report` + `commit_draft_version` RPC |
| `skills/neolyst/scripts/draft_report.py` | 新建 | Python 接口：生成 report_id、串联两个 RPC、中间上传文件 |
| `skills/neolyst/tests/test_draft_report.py` | 新建 | 集成测试（13 个测试） |
| `skills/neolyst/SKILL.md` | 修改 | 将 save_draft_report 标记为 ✅ 已实现，更新文件路径说明 |
| `docs/skills_neolyst_design.md` | 修改 | 更新报告 bucket 路径规则为 `{report_id}/v{version_no}/{filename}` |

---

## 背景与约束

- `report` 表：`id uuid primary key`、`title text not null`、`report_type text not null`、`status text default 'draft'`、`current_version_no integer default 0`、`owner_user_id uuid not null`
- `report_version` 表：`(report_id, version_no)` 唯一约束；`version_no >= 1`；`snapshot_json jsonb not null`；`created_by uuid not null`
- `report_analyst` 表：`(report_id, analyst_email)` 唯一约束；`(report_id, author_order)` 唯一约束
- Storage `reports_insert` policy：analyst 上传前 report 必须已在 DB → 流程改为先调 `init_draft_report` 建 report，再上传文件
- Storage 路径规则：`reports/{report_id}/v{version_no}/{原始文件名}`，v1/v2/... 目录分隔，历史版本不被覆盖
- 测试账号：`yangxue@opendelp.com` / `Admin123`（admin 角色）
- 测试 URL：`http://127.0.0.1:54321`

---

## Task 1: Supabase 迁移

**Files:**
- Create: `supabase/migrations/20260409000640_070_draft_report_functions.sql`

- [ ] **Step 1: 创建迁移文件**

```sql
-- 20260409000640_070_draft_report_functions.sql
-- ra_delete policy + init_draft_report + commit_draft_version RPC

-- ----------------------------------------------------------------
-- ra_delete policy：analyst 可删除自己报告的 report_analyst 记录
-- ----------------------------------------------------------------

create policy ra_delete
on public.report_analyst
for delete
to authenticated
using (
    public.current_app_role() = 'admin'
    or (
        public.current_app_role() = 'analyst'
        and exists (
            select 1 from public.report r
            where r.id = report_analyst.report_id
              and r.owner_user_id = auth.uid()
        )
    )
);

-- ----------------------------------------------------------------
-- init_draft_report：创建/更新 report + 全量替换 report_analyst
-- 返回 report_id 和 next_version_no，供 Python 侧上传文件后调用 commit_draft_version
-- ----------------------------------------------------------------

create or replace function public.init_draft_report(
    p_draft jsonb
)
returns table(report_id uuid, next_version_no integer)
language plpgsql
as $$
declare
    v_report_id      uuid;
    v_next_version   integer;
    v_is_new         boolean;
    v_analyst        jsonb;
begin
    v_report_id := (p_draft->>'report_id')::uuid;

    if v_report_id is null then
        raise exception 'report_id 不能为空，请在调用前用 uuid.uuid4() 生成';
    end if;

    if p_draft->'analysts' is null or jsonb_array_length(p_draft->'analysts') = 0 then
        raise exception 'analysts 不能为空';
    end if;

    select not exists(
        select 1 from public.report where id = v_report_id
    ) into v_is_new;

    if v_is_new then
        v_next_version := 1;

        insert into public.report (
            id, title, report_type, status, current_version_no, owner_user_id,
            coverage_id, ticker, sector_id, region_code, rating, target_price,
            investment_thesis, report_language, contact_person
        ) values (
            v_report_id,
            p_draft->>'title',
            p_draft->>'report_type',
            'draft',
            0,
            auth.uid(),
            (p_draft->>'coverage_id')::uuid,
            p_draft->>'ticker',
            (p_draft->>'sector_id')::uuid,
            p_draft->>'region_code',
            p_draft->>'rating',
            (p_draft->>'target_price')::numeric,
            p_draft->>'investment_thesis',
            p_draft->>'report_language',
            p_draft->>'contact_person'
        );
    else
        select r.current_version_no + 1 into v_next_version
        from public.report r
        where r.id = v_report_id;

        update public.report set
            title             = p_draft->>'title',
            report_type       = p_draft->>'report_type',
            coverage_id       = (p_draft->>'coverage_id')::uuid,
            ticker            = p_draft->>'ticker',
            sector_id         = (p_draft->>'sector_id')::uuid,
            region_code       = p_draft->>'region_code',
            rating            = p_draft->>'rating',
            target_price      = (p_draft->>'target_price')::numeric,
            investment_thesis = p_draft->>'investment_thesis',
            report_language   = p_draft->>'report_language',
            contact_person    = p_draft->>'contact_person'
        where id = v_report_id;
    end if;

    -- 全量替换 report_analyst
    delete from public.report_analyst where report_id = v_report_id;

    for v_analyst in select * from jsonb_array_elements(p_draft->'analysts')
    loop
        insert into public.report_analyst (report_id, analyst_email, author_order)
        values (
            v_report_id,
            lower(btrim(v_analyst->>'analyst_email')),
            (v_analyst->>'author_order')::integer
        );
    end loop;

    return query select v_report_id, v_next_version;
end;
$$;

comment on function public.init_draft_report is
'第一步：创建或更新 report 主表字段，全量替换 report_analyst。
返回 next_version_no 供 Python 侧上传文件到正确路径后调用 commit_draft_version。
不写入 report_version，不更新 current_version_no。';

revoke execute on function public.init_draft_report from public, anon;
grant execute on function public.init_draft_report to authenticated;

-- ----------------------------------------------------------------
-- commit_draft_version：插入 report_version + 更新 current_version_no
-- 在 Python 上传完文件后调用
-- ----------------------------------------------------------------

create or replace function public.commit_draft_version(
    p_report_id     uuid,
    p_version_no    integer,
    p_word_path     text,
    p_pdf_path      text,
    p_model_path    text,
    p_snapshot      jsonb
)
returns table(report_id uuid, version_no integer, status text)
language plpgsql
as $$
begin
    insert into public.report_version (
        report_id, version_no, snapshot_json,
        word_file_path, pdf_file_path, model_file_path, created_by
    ) values (
        p_report_id, p_version_no, p_snapshot,
        p_word_path, p_pdf_path, p_model_path,
        auth.uid()
    );

    update public.report set
        current_version_no = p_version_no
    where id = p_report_id;

    return query
        select p_report_id, p_version_no, 'draft'::text;
end;
$$;

comment on function public.commit_draft_version is
'第二步：文件上传完成后调用。插入 report_version 快照，更新 report.current_version_no。';

revoke execute on function public.commit_draft_version from public, anon;
grant execute on function public.commit_draft_version to authenticated;
```

- [ ] **Step 2: 应用迁移**

```bash
cd /mnt/c/_code/neoskills
supabase migration up
```

若出现错误，全量重置：

```bash
supabase db reset
```

- [ ] **Step 3: 验证两个 RPC 存在**

```bash
cd /mnt/c/_code/neoskills
uv run python -c "
from skills.neolyst.scripts import connection
client = connection.get_client()
try:
    client.rpc('init_draft_report', {'p_draft': {}}).execute()
except Exception as e:
    print('init_draft_report 错误（期望含 report_id 不能为空）:', e)
print('验证完成')
"
```

Expected: 输出包含 `report_id 不能为空`

---

## Task 2: 实现 draft_report.py

**Files:**
- Create: `skills/neolyst/scripts/draft_report.py`

- [ ] **Step 1: 创建 draft_report.py**

```python
"""
draft_report.py — Neolyst draft 报告保存接口。

执行流程（支持 analyst 权限）：
1. 若 report_id 为 None，用 uuid.uuid4() 生成
2. 调用 init_draft_report RPC → 建/更新 report + 替换 report_analyst → 返回 next_version_no
3. 上传本地文件到 reports/{report_id}/v{version_no}/{原始文件名}
   （此时 report 已在 DB，analyst 的 Storage 权限不受阻）
4. 调用 commit_draft_version RPC → 插入 report_version + 更新 current_version_no
5. 返回 {report_id, version_no, status}

业务逻辑全部在 Supabase RPC 侧，本模块只做 I/O 和参数整理。
"""

import uuid
from pathlib import Path

from supabase import Client

from skills.neolyst.scripts import storage


def save_draft_report(client: Client, draft: dict) -> dict:
    """
    保存 draft 报告（新建或追加版本）。

    Args:
        client: 已认证的 Supabase client
        draft: 扁平化 draft 输入 dict，支持以下字段：
            - report_id (str | None): 已有报告 UUID；None 时自动生成
            - title (str): 报告标题（必填）
            - report_type (str): 报告类型，如 "company"、"sector"（必填）
            - report_language (str | None): "zh" 或 "en"
            - analysts (list[dict]): [{"analyst_email": "...", "author_order": 1}, ...]（必填）
            - report_file (str | None): Word 文件本地路径
            - pdf_file (str | None): PDF 文件本地路径
            - model_file (str | None): 财务模型文件本地路径（可选）
            - coverage_id (str | None): coverage UUID
            - ticker (str | None): 股票代码
            - rating (str | None): 投资评级
            - target_price (float | None): 目标价
            - region_code (str | None): 区域编码
            - sector_id (str | None): 行业 UUID
            - contact_person (str | None): 联系人邮箱
            - investment_thesis (str | None): 投资论点

    Returns:
        dict: {"report_id": "uuid字符串", "version_no": int, "status": "draft"}

    Raises:
        FileNotFoundError: 本地文件不存在
        ValueError: RPC 调用失败（含具体错误信息）
    """
    # 1. 确定 report_id
    report_id = draft.get("report_id") or str(uuid.uuid4())

    # 2. 调用 init_draft_report：建/更新 report + 全量替换 report_analyst
    exclude_local = {"report_file", "pdf_file", "model_file"}
    p_draft = {k: v for k, v in draft.items() if k not in exclude_local}
    p_draft["report_id"] = report_id

    try:
        init_resp = client.rpc("init_draft_report", {"p_draft": p_draft}).execute()
    except Exception as e:
        raise ValueError(str(e)) from e

    version_no = init_resp.data[0]["next_version_no"]

    # 3. 上传文件到 reports/{report_id}/v{version_no}/{原始文件名}
    def _upload(local_path: str | None) -> str | None:
        if not local_path:
            return None
        filename = Path(local_path).name
        storage_path = f"reports/{report_id}/v{version_no}/{filename}"
        storage.upload(client, storage_path, local_path)
        return storage_path

    word_file_path = _upload(draft.get("report_file"))
    pdf_file_path = _upload(draft.get("pdf_file"))
    model_file_path = _upload(draft.get("model_file"))

    # 4. 构建 snapshot（p_draft 已排除本地路径，加入 storage 路径）
    snapshot = dict(p_draft)
    if word_file_path:
        snapshot["word_file_path"] = word_file_path
    if pdf_file_path:
        snapshot["pdf_file_path"] = pdf_file_path
    if model_file_path:
        snapshot["model_file_path"] = model_file_path

    # 5. 调用 commit_draft_version：插入 report_version + 更新 current_version_no
    try:
        commit_resp = client.rpc("commit_draft_version", {
            "p_report_id": report_id,
            "p_version_no": version_no,
            "p_word_path": word_file_path,
            "p_pdf_path": pdf_file_path,
            "p_model_path": model_file_path,
            "p_snapshot": snapshot,
        }).execute()
    except Exception as e:
        raise ValueError(str(e)) from e

    row = commit_resp.data[0]
    return {
        "report_id": str(row["report_id"]),
        "version_no": row["version_no"],
        "status": row["status"],
    }
```

- [ ] **Step 2: 验证 import**

```bash
cd /mnt/c/_code/neoskills
uv run python -c "from skills.neolyst.scripts import draft_report; print('OK')"
```

Expected: `OK`

---

## Task 3: 集成测试

**Files:**
- Create: `skills/neolyst/tests/test_draft_report.py`

- [ ] **Step 1: 创建 test_draft_report.py**

```python
"""
test_draft_report.py — save_draft_report 集成测试。
"""
import uuid
from pathlib import Path

import pytest


TEST_ANALYST = "yangxue@opendelp.com"


# ── module-level fixtures ────────────────────────────────────────────

@pytest.fixture(scope="module")
def tmp_module_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("draft_report")


def _make_files(directory: Path) -> tuple[str, str]:
    word = directory / "report.docx"
    pdf = directory / "report.pdf"
    word.write_bytes(b"fake docx content for test")
    pdf.write_bytes(b"fake pdf content for test")
    return str(word), str(pdf)


@pytest.fixture(scope="module")
def first_save_result(neolyst_client, tmp_module_dir):
    """首次保存（report_id=None），模块结束后清理 report 及 storage 文件。"""
    from skills.neolyst.scripts import draft_report

    word_path, pdf_path = _make_files(tmp_module_dir)
    result = draft_report.save_draft_report(neolyst_client, {
        "report_id": None,
        "title": "Test Draft Report Iter4",
        "report_type": "company",
        "report_language": "en",
        "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
        "ticker": "TSTDR01",
        "coverage_id": None,
        "rating": None,
        "target_price": None,
        "region_code": None,
        "sector_id": None,
        "contact_person": None,
        "investment_thesis": None,
        "report_file": word_path,
        "pdf_file": pdf_path,
        "model_file": None,
    })
    yield result
    # Teardown: 删除 report（级联删除 report_version/report_analyst）
    neolyst_client.table("report").delete().eq("id", result["report_id"]).execute()
    # 清理 storage（v1/ 目录）
    report_id = result["report_id"]
    try:
        neolyst_client.storage.from_("reports").remove([
            f"{report_id}/v1/report.docx",
            f"{report_id}/v1/report.pdf",
            f"{report_id}/v2/report.docx",
            f"{report_id}/v2/report.pdf",
        ])
    except Exception:
        pass


@pytest.fixture(scope="module")
def second_save_result(neolyst_client, first_save_result, tmp_module_dir):
    """基于同一 report_id 的第二次保存（更新 title/rating）。"""
    from skills.neolyst.scripts import draft_report

    word_path, pdf_path = _make_files(tmp_module_dir)
    return draft_report.save_draft_report(neolyst_client, {
        "report_id": first_save_result["report_id"],
        "title": "Test Draft Report Iter4 v2",
        "report_type": "company",
        "report_language": "en",
        "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
        "ticker": "TSTDR01",
        "coverage_id": None,
        "rating": "OUTPERFORM",
        "target_price": 100.0,
        "region_code": None,
        "sector_id": None,
        "contact_person": TEST_ANALYST,
        "investment_thesis": "Updated thesis",
        "report_file": word_path,
        "pdf_file": pdf_path,
        "model_file": None,
    })


# ── happy path ───────────────────────────────────────────────────────

class TestSaveDraftNewReport:
    def test_returns_report_id_uuid(self, first_save_result):
        """首次保存返回合法 UUID 字符串的 report_id。"""
        assert first_save_result["report_id"]
        uuid.UUID(first_save_result["report_id"])

    def test_returns_version_no_1(self, first_save_result):
        """首次保存 version_no == 1。"""
        assert first_save_result["version_no"] == 1

    def test_returns_status_draft(self, first_save_result):
        """首次保存 status == 'draft'。"""
        assert first_save_result["status"] == "draft"

    def test_report_record_exists(self, neolyst_client, first_save_result):
        """report 表有对应记录，核心字段正确。"""
        resp = (
            neolyst_client.table("report")
            .select("*")
            .eq("id", first_save_result["report_id"])
            .execute()
        )
        assert resp.data
        record = resp.data[0]
        assert record["title"] == "Test Draft Report Iter4"
        assert record["report_type"] == "company"
        assert record["status"] == "draft"
        assert record["current_version_no"] == 1

    def test_report_version_record_exists(self, neolyst_client, first_save_result):
        """report_version 表有 version_no=1，file_path 含 v1/，snapshot 含 analysts 不含本地路径。"""
        resp = (
            neolyst_client.table("report_version")
            .select("*")
            .eq("report_id", first_save_result["report_id"])
            .eq("version_no", 1)
            .execute()
        )
        assert resp.data
        record = resp.data[0]
        assert "/v1/" in record["word_file_path"]
        assert "/v1/" in record["pdf_file_path"]
        snapshot = record["snapshot_json"]
        assert "analysts" in snapshot
        assert "report_file" not in snapshot
        assert "pdf_file" not in snapshot
        assert "model_file" not in snapshot

    def test_report_analyst_records_exist(self, neolyst_client, first_save_result):
        """report_analyst 表有 author_order=1 的分析师记录。"""
        resp = (
            neolyst_client.table("report_analyst")
            .select("*")
            .eq("report_id", first_save_result["report_id"])
            .execute()
        )
        assert len(resp.data) == 1
        assert resp.data[0]["analyst_email"] == TEST_ANALYST
        assert resp.data[0]["author_order"] == 1

    def test_storage_files_uploaded(self, neolyst_client, first_save_result):
        """Storage reports/{report_id}/v1/ 中有 report.docx 和 report.pdf。"""
        report_id = first_save_result["report_id"]
        files = neolyst_client.storage.from_("reports").list(f"{report_id}/v1")
        names = [f["name"] for f in files]
        assert "report.docx" in names
        assert "report.pdf" in names


class TestSaveDraftSecondVersion:
    def test_same_report_id(self, first_save_result, second_save_result):
        """第二次保存沿用同一 report_id。"""
        assert second_save_result["report_id"] == first_save_result["report_id"]

    def test_version_no_incremented(self, second_save_result):
        """第二次保存 version_no == 2。"""
        assert second_save_result["version_no"] == 2

    def test_report_current_version_updated(self, neolyst_client, second_save_result):
        """report.current_version_no 更新为 2，title 和 rating 为新值。"""
        resp = (
            neolyst_client.table("report")
            .select("current_version_no, title, rating")
            .eq("id", second_save_result["report_id"])
            .execute()
        )
        record = resp.data[0]
        assert record["current_version_no"] == 2
        assert record["title"] == "Test Draft Report Iter4 v2"
        assert record["rating"] == "OUTPERFORM"

    def test_v2_files_in_separate_dir(self, neolyst_client, second_save_result):
        """v2 文件存储在 v2/ 目录，不覆盖 v1/ 文件。"""
        report_id = second_save_result["report_id"]
        files_v2 = neolyst_client.storage.from_("reports").list(f"{report_id}/v2")
        names = [f["name"] for f in files_v2]
        assert "report.docx" in names
        assert "report.pdf" in names


# ── error cases ──────────────────────────────────────────────────────

class TestSaveDraftErrors:
    def test_missing_title_raises(self, neolyst_client, tmp_path):
        """title 为 None 时 NOT NULL 违规，包装为 ValueError。"""
        from skills.neolyst.scripts import draft_report

        word = tmp_path / "r.docx"
        word.write_bytes(b"x")
        pdf = tmp_path / "r.pdf"
        pdf.write_bytes(b"x")

        with pytest.raises(ValueError):
            draft_report.save_draft_report(neolyst_client, {
                "report_id": None,
                "title": None,
                "report_type": "company",
                "report_language": "en",
                "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
                "report_file": str(word),
                "pdf_file": str(pdf),
            })

    def test_empty_analysts_raises(self, neolyst_client, tmp_path):
        """analysts 为空列表时 RPC 抛出"analysts 不能为空"。"""
        from skills.neolyst.scripts import draft_report

        word = tmp_path / "r.docx"
        word.write_bytes(b"x")
        pdf = tmp_path / "r.pdf"
        pdf.write_bytes(b"x")

        with pytest.raises(ValueError, match="analysts 不能为空"):
            draft_report.save_draft_report(neolyst_client, {
                "report_id": None,
                "title": "Error Test",
                "report_type": "company",
                "report_language": "en",
                "analysts": [],
                "report_file": str(word),
                "pdf_file": str(pdf),
            })
```

- [ ] **Step 2: 运行 draft_report 测试**

```bash
cd /mnt/c/_code/neoskills
NEOLYST_URL=http://127.0.0.1:54321 uv run --with pytest pytest skills/neolyst/tests/test_draft_report.py -v
```

Expected: 13 tests PASSED（TestSaveDraftNewReport: 7, TestSaveDraftSecondVersion: 4, TestSaveDraftErrors: 2）

- [ ] **Step 3: 全量测试**

```bash
NEOLYST_URL=http://127.0.0.1:54321 uv run --with pytest pytest skills/neolyst/tests/ -v
```

Expected: 全部通过（含 iter1~3 的 26 个，合计 39 个）

- [ ] **Step 4: Commit**

```bash
git add \
    supabase/migrations/20260409000640_070_draft_report_functions.sql \
    skills/neolyst/scripts/draft_report.py \
    skills/neolyst/tests/test_draft_report.py
git commit -m "feat: add draft_report with init_draft_report and commit_draft_version RPC"
```

---

## Task 4: 更新 SKILL.md 和设计文档

**Files:**
- Modify: `skills/neolyst/SKILL.md`
- Modify: `docs/skills_neolyst_design.md`

- [ ] **Step 1: 将 save_draft_report 标记为已实现，更新文件路径说明**

将第 185 行：

```markdown
### 7. save_draft_report 🔲 待实现
```

改为：

```markdown
### 7. save_draft_report ✅ 已实现
```

将示例代码块后（"字段分层："之前）补充一行：

```markdown
报告文件存储路径：`reports/{report_id}/v{version_no}/{原始文件名}`，各版本独立目录，不互相覆盖。
```

- [ ] **Step 2: 更新 docs/skills_neolyst_design.md 报告 bucket 路径规则**

将 `docs/skills_neolyst_design.md` 第 87 行：

```
- 报告 bucket 路径规则：`{report_id}/`（具体文件名由 `storage.py` 统一维护）。
```

改为：

```
- 报告 bucket 路径规则：`{report_id}/v{version_no}/{原始文件名}`。路径由 `draft_report.py` 在 `commit_draft_version` 前生成，文件名保留调用方传入的原始文件名（`Path(local_path).name`），版本间文件存储在独立目录下互不覆盖。
```

- [ ] **Step 3: Commit**

```bash
git add skills/neolyst/SKILL.md docs/skills_neolyst_design.md
git commit -m "docs: update save_draft_report to implemented, fix report storage path rule"
```

---

## Task 5: 更新路线图

**Files:**
- Modify: `plans/2026-04-07-neolyst-skill-roadmap.md`

- [ ] **Step 1: 标记 Iter 4 完成**

将：

```
| Iter 4 | draft_report | 未开始 | — |
```

改为：

```
| Iter 4 | draft_report | 已完成 | [2026-04-09-neolyst-iter4.md](2026-04-09-neolyst-iter4.md) |
```

- [ ] **Step 2: Commit**

```bash
git add plans/2026-04-07-neolyst-skill-roadmap.md
git commit -m "docs: mark iter4 complete, update roadmap"
```

---

## 自检

- [ ] 迁移文件包含：`ra_delete` policy、`init_draft_report` RPC、`commit_draft_version` RPC，均 grant 给 authenticated，无 SECURITY DEFINER
- [ ] `init_draft_report`：新建 report（current_version_no=0）或更新 report 字段；全量替换 report_analyst；返回 {report_id, next_version_no}
- [ ] `commit_draft_version`：插入 report_version；更新 report.current_version_no；返回 {report_id, version_no, status}
- [ ] `draft_report.py`：流程顺序为 init → upload → commit；文件路径含 v{version_no}；snapshot 排除本地路径含 storage 路径
- [ ] 13 个集成测试通过（7+4+2）；v2 文件在 v2/ 目录验证了版本隔离
- [ ] 全量 39 个测试通过
- [ ] SKILL.md save_draft_report 标记为 ✅ 已实现，含文件路径说明
- [ ] `docs/skills_neolyst_design.md` 报告 bucket 路径规则更新为 `{report_id}/v{version_no}/{原始文件名}`
- [ ] roadmap Iter 4 标记已完成
