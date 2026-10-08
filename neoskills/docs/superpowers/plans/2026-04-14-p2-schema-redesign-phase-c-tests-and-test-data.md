# P2 Schema Redesign Phase C Tests And Test Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让测试与 `supabase/tests/test_data.sql` 全部切换到 P2 的“路径字段在 report 表、无 report_version、无 version_no/current_version_no”模型，并新增上传流程覆盖。

**Architecture:** Phase C 不再假设版本号目录或 `report_version` 快照存在。测试通过 `save_report` + `upload_report_files` + `upload_model_file` 组合出真实用户路径，并用正则匹配时间戳目录；静态 SQL 测试数据直接在 `report` 上落 `word_path/pdf_path/model_path`，状态日志只保留 metadata 和状态流转，不再保留版本号列。

**Tech Stack:** `pytest`、`uv`、Supabase test client、`supabase/tests/test_data.sql`

---

## File Map

| 路径 | 角色 |
|---|---|
| `skills/neolyst/tests/test_save_report.py` | 由 `test_draft_report.py` 改名，改成只测 metadata 保存 |
| `skills/neolyst/tests/test_upload_files.py` | 新增，覆盖 Word/PDF/Model 上传与替换 |
| `skills/neolyst/tests/test_submit_report.py` | 改成基于新 client 流程建数，去掉 version 断言 |
| `skills/neolyst/tests/test_retract_report.py` | 改成基于新 client 流程建数，去掉 version 断言 |
| `skills/neolyst/tests/test_validators.py` | 改成校验 report 上的路径字段，不再触碰 current_version_no/report_version |
| `skills/neolyst/tests/test_coverage.py` | fixture 去掉 `current_version_no` |
| `skills/neolyst/tests/conftest.py` | 只读参考：复用现有 client/bucket fixture |
| `supabase/tests/test_data.sql` | 静态测试数据：删除 `report_version` 段，改用 `report.word_path/pdf_path/model_path` 和无 `version_no` 的状态日志 |

## Task 1: 把 `test_draft_report.py` 改成 `test_save_report.py`

**Files:**
- Move: `skills/neolyst/tests/test_draft_report.py` → `skills/neolyst/tests/test_save_report.py`
- Reference: `skills/neolyst/tests/conftest.py`

- [ ] **Step 1: 重命名测试文件，切断旧命名**

Run:

```bash
git mv skills/neolyst/tests/test_draft_report.py skills/neolyst/tests/test_save_report.py
```

Expected:

```text
git status 中出现 test_draft_report.py -> test_save_report.py 的 rename
```

- [ ] **Step 2: 重写 helper，只构造 metadata 保存，不再生成版本目录**

把 [test_save_report.py](/mnt/c/_code/neoskills/skills/neolyst/tests/test_save_report.py) 的开头 helper 改成下面这样：

```python
"""
test_save_report.py — save_report 集成测试。
"""
import json
import uuid
from pathlib import Path

import pytest

TEST_ANALYST = json.loads((Path(__file__).parent / "test_config.json").read_text())["email"]


@pytest.fixture(scope="module")
def tmp_module_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("save_report")


def _base_payload(**overrides):
    payload = {
        "report_id": None,
        "title": "Test Save Report",
        "report_type": "company",
        "report_language": "en",
        "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
        "ticker": "TSAVE01",
        "coverage_id": None,
        "rating": None,
        "target_price": None,
        "region_code": None,
        "sector_id": None,
        "contact_person": None,
        "investment_thesis": None,
        "report_file": "/tmp/ignored.docx",
        "pdf_file": "/tmp/ignored.pdf",
        "model_file": "/tmp/ignored.xlsx",
    }
    payload.update(overrides)
    return payload
```

- [ ] **Step 3: 把 happy path 改成“路径字段初始为空 + 二次保存不改路径”**

核心测试块替换成下面这样：

```python
class TestSaveReport:
    def test_returns_report_id_uuid(self, neolyst_client):
        from skills.neolyst.scripts import save_report

        result = save_report.save_report(neolyst_client, _base_payload())
        try:
            assert result["report_id"]
            uuid.UUID(result["report_id"])
        finally:
            neolyst_client.table("report").delete().eq("id", result["report_id"]).execute()

    def test_new_report_has_null_paths(self, neolyst_client):
        from skills.neolyst.scripts import save_report

        result = save_report.save_report(neolyst_client, _base_payload(title="Null Paths Test"))
        try:
            resp = (
                neolyst_client.table("report")
                .select("status, word_path, pdf_path, model_path")
                .eq("id", result["report_id"])
                .execute()
            )
            row = resp.data[0]
            assert row["status"] == "draft"
            assert row["word_path"] is None
            assert row["pdf_path"] is None
            assert row["model_path"] is None
        finally:
            neolyst_client.table("report").delete().eq("id", result["report_id"]).execute()

    def test_update_metadata_keeps_existing_paths(self, neolyst_client, tmp_path):
        from skills.neolyst.scripts import save_report, upload_files

        word = tmp_path / "report.docx"
        pdf = tmp_path / "report.pdf"
        model = tmp_path / "model.xlsx"
        word.write_bytes(b"fake docx")
        pdf.write_bytes(b"fake pdf")
        model.write_bytes(b"fake xlsx")

        first = save_report.save_report(neolyst_client, _base_payload(title="Initial Title"))
        report_id = first["report_id"]
        try:
            uploaded = upload_files.upload_report_files(neolyst_client, report_id, str(word), str(pdf))
            model_uploaded = upload_files.upload_model_file(neolyst_client, report_id, str(model))

            save_report.save_report(neolyst_client, _base_payload(
                report_id=report_id,
                title="Updated Title",
                rating="OUTPERFORM",
                contact_person=TEST_ANALYST,
                investment_thesis="Updated thesis",
            ))

            resp = (
                neolyst_client.table("report")
                .select("title, rating, word_path, pdf_path, model_path")
                .eq("id", report_id)
                .execute()
            )
            row = resp.data[0]
            assert row["title"] == "Updated Title"
            assert row["rating"] == "OUTPERFORM"
            assert row["word_path"] == uploaded["word_path"]
            assert row["pdf_path"] == uploaded["pdf_path"]
            assert row["model_path"] == model_uploaded["model_path"]
        finally:
            neolyst_client.table("report").delete().eq("id", report_id).execute()
```

- [ ] **Step 4: 删除旧的版本号 / report_version / Storage `v1/v2` 断言**

Run:

```bash
rg -n "version_no|current_version_no|report_version|/v1|/v2|save_draft_report|draft_report" skills/neolyst/tests/test_save_report.py
```

Expected:

```text
只保留 save_report / upload_files 新调用；不再命中旧版本模型相关断言
```

## Task 2: 新增 `test_upload_files.py`

**Files:**
- Create: `skills/neolyst/tests/test_upload_files.py`

- [ ] **Step 1: 新建测试文件，覆盖 Word/PDF 上传、Model 上传和替换路径**

新文件直接写成下面这样：

```python
"""
test_upload_files.py — upload_report_files / upload_model_file 集成测试。
"""
import json
import re
import time
from pathlib import Path

TEST_ANALYST = json.loads((Path(__file__).parent / "test_config.json").read_text())["email"]


def _make_files(directory: Path, prefix: str = "report") -> tuple[str, str, str]:
    directory.mkdir(parents=True, exist_ok=True)
    word = directory / f"{prefix}.docx"
    pdf = directory / f"{prefix}.pdf"
    model = directory / f"{prefix}.xlsx"
    word.write_bytes(b"fake docx")
    pdf.write_bytes(b"fake pdf")
    model.write_bytes(b"fake xlsx")
    return str(word), str(pdf), str(model)


def _create_report(client):
    from skills.neolyst.scripts import save_report

    return save_report.save_report(client, {
        "report_id": None,
        "title": "Upload Files Test",
        "report_type": "company",
        "report_language": "en",
        "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
        "ticker": "UPLD001",
        "coverage_id": None,
        "rating": None,
        "target_price": None,
        "region_code": None,
        "sector_id": None,
        "contact_person": TEST_ANALYST,
        "investment_thesis": "upload test thesis",
    })["report_id"]


def _strip_bucket(storage_path: str) -> str:
    return storage_path.split("/", 1)[1]


def test_upload_report_files_updates_report_and_storage(neolyst_client, tmp_path):
    from skills.neolyst.scripts import upload_files

    report_id = _create_report(neolyst_client)
    word, pdf, _ = _make_files(tmp_path / "docs")
    try:
        result = upload_files.upload_report_files(neolyst_client, report_id, word, pdf)
        assert re.match(rf"^reports/{report_id}/report/\\d{{8}}_\\d{{6}}/report\\.docx$", result["word_path"])
        assert re.match(rf"^reports/{report_id}/report/\\d{{8}}_\\d{{6}}/report\\.pdf$", result["pdf_path"])
        assert result["word_path"].rsplit("/", 1)[0] == result["pdf_path"].rsplit("/", 1)[0]

        row = (
            neolyst_client.table("report")
            .select("word_path, pdf_path")
            .eq("id", report_id)
            .execute()
            .data[0]
        )
        assert row["word_path"] == result["word_path"]
        assert row["pdf_path"] == result["pdf_path"]

        prefix = _strip_bucket(result["word_path"]).rsplit("/", 1)[0]
        names = [item["name"] for item in neolyst_client.storage.from_("reports").list(prefix)]
        assert "report.docx" in names
        assert "report.pdf" in names
    finally:
        neolyst_client.table("report").delete().eq("id", report_id).execute()


def test_upload_model_file_updates_only_model_path(neolyst_client, tmp_path):
    from skills.neolyst.scripts import upload_files

    report_id = _create_report(neolyst_client)
    word, pdf, model = _make_files(tmp_path / "model")
    try:
        docs = upload_files.upload_report_files(neolyst_client, report_id, word, pdf)
        uploaded_model = upload_files.upload_model_file(neolyst_client, report_id, model)

        row = (
            neolyst_client.table("report")
            .select("word_path, pdf_path, model_path")
            .eq("id", report_id)
            .execute()
            .data[0]
        )
        assert row["word_path"] == docs["word_path"]
        assert row["pdf_path"] == docs["pdf_path"]
        assert row["model_path"] == uploaded_model["model_path"]
        assert re.match(rf"^reports/{report_id}/model/\\d{{8}}_\\d{{6}}/report\\.xlsx$", uploaded_model["model_path"])
    finally:
        neolyst_client.table("report").delete().eq("id", report_id).execute()


def test_reupload_keeps_old_storage_objects(neolyst_client, tmp_path):
    from skills.neolyst.scripts import upload_files

    report_id = _create_report(neolyst_client)
    first_word, first_pdf, _ = _make_files(tmp_path / "first", "first_report")
    second_word, second_pdf, _ = _make_files(tmp_path / "second", "second_report")
    try:
        first = upload_files.upload_report_files(neolyst_client, report_id, first_word, first_pdf)
        time.sleep(1.1)
        second = upload_files.upload_report_files(neolyst_client, report_id, second_word, second_pdf)

        assert first["word_path"] != second["word_path"]
        assert first["pdf_path"] != second["pdf_path"]

        first_prefix = _strip_bucket(first["word_path"]).rsplit("/", 1)[0]
        second_prefix = _strip_bucket(second["word_path"]).rsplit("/", 1)[0]
        first_names = [item["name"] for item in neolyst_client.storage.from_("reports").list(first_prefix)]
        second_names = [item["name"] for item in neolyst_client.storage.from_("reports").list(second_prefix)]
        assert "first_report.docx" in first_names
        assert "second_report.docx" in second_names
    finally:
        neolyst_client.table("report").delete().eq("id", report_id).execute()
```

- [ ] **Step 2: 单独跑上传测试，确认时间戳目录断言稳定**

Run:

```bash
uv run pytest skills/neolyst/tests/test_upload_files.py -q
```

Expected:

```text
3 passed
```

## Task 3: 更新 `submit` / `retract` / `validators` 测试到新流程

**Files:**
- Modify: `skills/neolyst/tests/test_submit_report.py`
- Modify: `skills/neolyst/tests/test_retract_report.py`
- Modify: `skills/neolyst/tests/test_validators.py`

- [ ] **Step 1: 在 `test_submit_report.py` 里把建数流程改成 `save_report + upload_report_files`**

把 `submitted_report` fixture 和关键断言改成下面这样：

```python
@pytest.fixture(scope="module")
def submitted_report(neolyst_client, submit_coverage_id, tmp_path_factory):
    from skills.neolyst.scripts import save_report, upload_files
    from skills.neolyst.scripts import submit_report as sr

    d = tmp_path_factory.mktemp("submit_test")
    word_path, pdf_path = _make_files(d)
    saved = save_report.save_report(neolyst_client, {
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
    })
    upload_files.upload_report_files(neolyst_client, saved["report_id"], word_path, pdf_path)
    result = sr.submit_report(neolyst_client, saved["report_id"])
    yield result
    neolyst_client.table("report").delete().eq("id", result["report_id"]).execute()


def test_returns_report_id(self, submitted_report):
    uuid.UUID(submitted_report["report_id"])
    assert submitted_report["status"] == "submitted"


def test_status_log_created(self, neolyst_client, submitted_report):
    resp = (
        neolyst_client.table("report_status_log")
        .select("*")
        .eq("report_id", submitted_report["report_id"])
        .execute()
    )
    log = resp.data[0]
    assert log["from_status"] == "draft"
    assert log["to_status"] == "submitted"
    assert log["metadata"]["title"] == "Submit Test Report"
    assert log["metadata"]["word_path"]
    assert log["metadata"]["pdf_path"]
```

- [ ] **Step 2: 用“路径字段为空”替换旧的 `current_version_no/report_version` 异常测试**

把 `test_submit_without_current_version_raises` 和 `test_submit_with_missing_current_version_row_raises` 改成下面两个测试：

```python
def test_submit_without_word_path_raises(self, neolyst_client, submit_coverage_id, tmp_path):
    from skills.neolyst.scripts import save_report, upload_files
    from skills.neolyst.scripts import submit_report as sr

    word_path, pdf_path = _make_files(tmp_path)
    saved = save_report.save_report(neolyst_client, {
        "report_id": None,
        "title": "Submit Missing Word",
        "report_type": "company",
        "report_language": "en",
        "investment_thesis": "Test investment thesis",
        "contact_person": TEST_ANALYST,
        "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
        "ticker": "SUBWORD",
        "coverage_id": submit_coverage_id,
    })
    try:
        upload_files.upload_report_files(neolyst_client, saved["report_id"], word_path, pdf_path)
        neolyst_client.table("report").update({"word_path": None}).eq("id", saved["report_id"]).execute()
        with pytest.raises(ValueError, match="Word"):
            sr.submit_report(neolyst_client, saved["report_id"])
    finally:
        neolyst_client.table("report").delete().eq("id", saved["report_id"]).execute()


def test_submit_without_pdf_path_raises(self, neolyst_client, submit_coverage_id, tmp_path):
    from skills.neolyst.scripts import save_report, upload_files
    from skills.neolyst.scripts import submit_report as sr

    word_path, pdf_path = _make_files(tmp_path)
    saved = save_report.save_report(neolyst_client, {
        "report_id": None,
        "title": "Submit Missing PDF",
        "report_type": "company",
        "report_language": "en",
        "investment_thesis": "Test investment thesis",
        "contact_person": TEST_ANALYST,
        "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
        "ticker": "SUBPDF",
        "coverage_id": submit_coverage_id,
    })
    try:
        upload_files.upload_report_files(neolyst_client, saved["report_id"], word_path, pdf_path)
        neolyst_client.table("report").update({"pdf_path": None}).eq("id", saved["report_id"]).execute()
        with pytest.raises(ValueError, match="PDF"):
            sr.submit_report(neolyst_client, saved["report_id"])
    finally:
        neolyst_client.table("report").delete().eq("id", saved["report_id"]).execute()
```

- [ ] **Step 3: 同步改 `test_retract_report.py` 和 `test_validators.py`**

把这两处核心 helper 分别替换为下面这样：

```python
def _create_submitted_report(client, coverage_id, tmp_dir, title="Retract Test"):
    from skills.neolyst.scripts import save_report, upload_files
    from skills.neolyst.scripts import submit_report as sr

    word_path, pdf_path = _make_files(tmp_dir)
    saved = save_report.save_report(client, {
        "report_id": None,
        "title": title,
        "report_type": "company",
        "report_language": "en",
        "investment_thesis": "Test investment thesis",
        "contact_person": TEST_ANALYST,
        "analysts": [{"analyst_email": TEST_ANALYST, "author_order": 1}],
        "ticker": title[:8].upper().replace(" ", ""),
        "coverage_id": coverage_id,
        "rating": "OUTPERFORM",
        "target_price": 100.0,
    })
    upload_files.upload_report_files(client, saved["report_id"], word_path, pdf_path)
    return sr.submit_report(client, saved["report_id"])
```

```python
def _save_report_with_files(client, directory, overrides=None):
    from skills.neolyst.scripts import save_report, upload_files

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
        "coverage_id": None,
        "sector_id": None,
        "region_code": None,
        "rating": None,
        "target_price": None,
    }
    if overrides:
        base.update(overrides)

    saved = save_report.save_report(client, base)
    upload_files.upload_report_files(client, saved["report_id"], word_path, pdf_path)
    return saved
```

然后把 `test_validators.py` 的旧版本错误测试替换成下面两条：

```python
def test_missing_word_path_fails(self, neolyst_client, test_coverage_id, tmp_path):
    from skills.neolyst.scripts.validators import validate_report

    result = _save_report_with_files(neolyst_client, tmp_path, {"coverage_id": test_coverage_id})
    try:
        neolyst_client.table("report").update({"word_path": None}).eq("id", result["report_id"]).execute()
        with pytest.raises(ValueError, match="Word"):
            validate_report(neolyst_client, result["report_id"])
    finally:
        _cleanup(neolyst_client, result["report_id"])


def test_missing_pdf_path_fails(self, neolyst_client, test_coverage_id, tmp_path):
    from skills.neolyst.scripts.validators import validate_report

    result = _save_report_with_files(neolyst_client, tmp_path, {"coverage_id": test_coverage_id})
    try:
        neolyst_client.table("report").update({"pdf_path": None}).eq("id", result["report_id"]).execute()
        with pytest.raises(ValueError, match="PDF"):
            validate_report(neolyst_client, result["report_id"])
    finally:
        _cleanup(neolyst_client, result["report_id"])
```

- [ ] **Step 4: 搜索测试目录，确认旧版本模型已被清掉**

Run:

```bash
rg -n "save_draft_report|draft_report|current_version_no|report_version|version_no|/v1|/v2" skills/neolyst/tests
```

Expected:

```text
仅允许命中仍未处理的 test_coverage.py 或 test_data.sql 迁移说明；Phase C 改过的测试文件里不再依赖旧版本模型
```

## Task 4: 更新 `test_coverage.py` 和 `supabase/tests/test_data.sql`

**Files:**
- Modify: `skills/neolyst/tests/test_coverage.py`
- Modify: `supabase/tests/test_data.sql`

- [ ] **Step 1: 先把 `test_coverage.py` fixture 里的 `current_version_no` 去掉**

把 `history_dataset` 里 3 个 `rows` 元素中的这段：

```python
"current_version_no": 1,
```

直接删掉，不新增替代字段；其余断言不需要改。

- [ ] **Step 2: 批量改 `test_data.sql` 里的 report insert**

把每个 `insert into public.report` 的列清单从：

```sql
id, title, report_type, status, current_version_no,
owner_user_id, coverage_id, ticker,
sector_id, region_code, rating, target_price,
investment_thesis, report_language, contact_person,
published_by, published_at
```

改成：

```sql
id, title, report_type, status, word_path, pdf_path, model_path,
owner_user_id, coverage_id, ticker,
sector_id, region_code, rating, target_price,
investment_thesis, report_language, contact_person,
published_by, published_at
```

对应 values 也一起改。例如第一条 published report 改成：

```sql
) values (
    'e0000000-0000-0000-0000-000000000001'::uuid,
    'Active Response to Energy Transition and Enhancement of Low-Carbon Power Amid AI Data Center Migration and Natural Gas Demand Growth: Initiation',
    'company', 'published',
    'reports/e0000000-0000-0000-0000-000000000001/report/20260104_163000/EN-Vistra_Corp20260104.docx',
    'reports/e0000000-0000-0000-0000-000000000001/report/20260104_163000/EN-Vistra_Corp20260104.pdf',
    'reports/e0000000-0000-0000-0000-000000000001/model/20260104_163000/EN-Vistra_Corp20260104.xlsx',
    'a0000000-0000-0000-0000-000000000010'::uuid,
    'c0000000-0000-0000-0000-000000000001'::uuid,
    'VST US',
    '00000000-0000-0000-0000-000000000079'::uuid,
    'US', 'OUTPERFORM', 423.72,
    'Vistra is well positioned as a leading integrated power generator benefiting from AI data center demand growth and energy transition.',
    'en', 'harryyang@hfisec.com.hk',
    'a0000000-0000-0000-0000-000000000002'::uuid,
    '2026-01-05 10:00:00+00'
)
```

对 7 条 report insert 全部做同样处理：
- draft 新建报告：`word_path/pdf_path/model_path` 可为 `null`
- submitted/published/rejected 报告：三列按新路径格式补齐
- 路径统一使用 `reports/{report_id}/report/{timestamp}/...` 和 `reports/{report_id}/model/{timestamp}/...`

- [ ] **Step 3: 删除整个 `report_version` 段，并更新状态日志 insert**

在 [test_data.sql](/mnt/c/_code/neoskills/supabase/tests/test_data.sql) 里：

1. 删除从下面这一行开始直到威胜控股 `report_version` 结束的所有块：

```sql
-- ============================================================
-- 6. 报告版本快照（public.report_version）
```

2. 把每个 `report_status_log` insert 的列清单从：

```sql
(id, report_id, from_status, to_status, action_by, action_by_name, version_no, action_at)
```

或：

```sql
(id, report_id, from_status, to_status, action_by, action_by_name, version_no, reason, action_at)
```

改成：

```sql
(id, report_id, from_status, to_status, action_by, action_by_name, action_at)
```

或：

```sql
(id, report_id, from_status, to_status, action_by, action_by_name, reason, action_at)
```

例如第一段改成：

```sql
insert into public.report_status_log (id, report_id, from_status, to_status, action_by, action_by_name, action_at)
values
    ('b0000000-0000-0000-0000-000000000001'::uuid,
     'e0000000-0000-0000-0000-000000000001'::uuid,
     'draft', 'submitted',
     'a0000000-0000-0000-0000-000000000010'::uuid, 'Bin Yang',
     '2026-01-04 16:30:00+00'),
```

- [ ] **Step 4: 回灌静态数据并跑整组测试**

Run:

```bash
supabase db reset
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres -f supabase/tests/test_data.sql
uv run pytest \
  skills/neolyst/tests/test_save_report.py \
  skills/neolyst/tests/test_upload_files.py \
  skills/neolyst/tests/test_submit_report.py \
  skills/neolyst/tests/test_retract_report.py \
  skills/neolyst/tests/test_validators.py \
  skills/neolyst/tests/test_coverage.py -q
```

Expected:

```text
test_data.sql 导入成功
上述 6 个测试文件全部通过
```

- [ ] **Step 5: 提交 Phase C**

Run:

```bash
git add skills/neolyst/tests/test_save_report.py skills/neolyst/tests/test_upload_files.py skills/neolyst/tests/test_submit_report.py skills/neolyst/tests/test_retract_report.py skills/neolyst/tests/test_validators.py skills/neolyst/tests/test_coverage.py supabase/tests/test_data.sql
git commit -m "test: align report schema redesign coverage"
```

Expected:

```text
成功创建只包含 Phase C 测试与 test_data.sql 改动的提交
```
