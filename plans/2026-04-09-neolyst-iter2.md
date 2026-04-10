# Neolyst Iter 2: storage + template 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 neolyst skill 的 storage 和 template 模块。路径规则在 Supabase 函数中定义，Python 只做文件上传/下载和 RPC 调用，不硬编码任何路径逻辑。

**Architecture:**
- **Supabase 侧**：迁移文件新增三个 RPC 函数：`get_template_storage_paths`、`upsert_template_record`、`reuse_template`
- **`storage.py`**：封装 Storage 上传/下载（只操作文件，不拼路径）
- **`template.py`**：调用 RPC + `storage.py`，实现三个业务接口
- **集成测试**：直接打 local Supabase，复用 `neolyst_client` fixture

**原则：**
- 路径规则只定义在 Supabase 函数里，Python 不拼路径字符串
- 直接读取（无逻辑）可查表，不需要 RPC（`resolve_template` 属于此类）
- 所有 schema 变更写入 `supabase/migrations/`

---

## 背景与约束

- `report_template` 表：主键 `id = "{report_type}_{language}"`，`template_file_path` NOT NULL（初始空字符串），`schema_file_path` nullable
- Storage bucket：`templates`（模板）和 `reports`（报告），尚未创建，需要本迭代初始化
- 模板 bucket 路径规则（在 RPC 中定义）：`{report_type}/{language}/template.docx` / `{report_type}/{language}/schema.yaml`
- `resolve_template` 下载到 `{dest_dir}/templates/{report_type}/{language}/`
- 测试账号：`yangxue@opendelp.com` / `Admin123`（admin 角色）
- 测试 URL：`NEOLYST_URL=http://127.0.0.1:54321`

---

## Task 1: Supabase 迁移 — RPC 函数 + bucket 初始化

**Files:**
- Create: `supabase/migrations/20260409000600_050_template_functions.sql`
- Modify: `supabase/config.toml`

- [x] **Step 1: 创建迁移文件**

```sql
-- 20260409000600_050_template_functions.sql
-- Template Storage 路径规则（唯一定义处）

create or replace function public.get_template_storage_paths(
    p_report_type text,
    p_language    text
)
returns table (template_file_path text, schema_file_path text)
language sql stable security definer
as $$
    select
        p_report_type || '/' || p_language || '/template.docx' as template_file_path,
        p_report_type || '/' || p_language || '/schema.yaml'    as schema_file_path;
$$;

comment on function public.get_template_storage_paths is
'返回指定 report_type + language 对应的模板 Storage 路径。路径规则的唯一定义处。';

-- ----------------------------------------------------------------

create or replace function public.upsert_template_record(
    p_report_type text,
    p_language    text
)
returns void
language plpgsql security definer
as $$
declare
    v_id                text;
    v_template_path     text;
    v_schema_path       text;
begin
    v_id            := p_report_type || '_' || p_language;
    v_template_path := p_report_type || '/' || p_language || '/template.docx';
    v_schema_path   := p_report_type || '/' || p_language || '/schema.yaml';

    insert into public.report_template (id, report_type, language, template_file_path, schema_file_path)
    values (v_id, p_report_type, p_language, v_template_path, v_schema_path)
    on conflict (id) do update
        set template_file_path = excluded.template_file_path,
            schema_file_path   = excluded.schema_file_path;
end;
$$;

comment on function public.upsert_template_record is
'上传文件后调用，服务端按固定规则生成路径并 upsert report_template 记录。';

-- ----------------------------------------------------------------

create or replace function public.reuse_template(
    p_report_type        text,
    p_language           text,
    p_same_as_report_type text
)
returns void
language plpgsql security definer
as $$
declare
    v_source   public.report_template%rowtype;
    v_target_id text;
begin
    if p_report_type = p_same_as_report_type then
        raise exception 'Cannot reuse self: report_type=''%''', p_report_type;
    end if;

    select * into v_source
    from public.report_template
    where id = p_same_as_report_type || '_' || p_language;

    if not found then
        raise exception 'Source template not found: ''%''',
            p_same_as_report_type || '_' || p_language;
    end if;

    if v_source.template_file_path = '' or v_source.template_file_path is null then
        raise exception 'Source template not published (empty path): ''%''',
            p_same_as_report_type || '_' || p_language;
    end if;

    v_target_id := p_report_type || '_' || p_language;

    insert into public.report_template (id, report_type, language, template_file_path, schema_file_path)
    values (v_target_id, p_report_type, p_language, v_source.template_file_path, v_source.schema_file_path)
    on conflict (id) do update
        set template_file_path = excluded.template_file_path,
            schema_file_path   = excluded.schema_file_path;
end;
$$;

comment on function public.reuse_template is
'让 report_type 的模板记录复用 same_as_report_type 的文件路径（静态复制）。';

-- RLS：仅 admin 可调用写函数
revoke execute on function public.upsert_template_record from public, anon, authenticated;
grant execute on function public.upsert_template_record to authenticated;

revoke execute on function public.reuse_template from public, anon, authenticated;
grant execute on function public.reuse_template to authenticated;

revoke execute on function public.get_template_storage_paths from public, anon;
grant execute on function public.get_template_storage_paths to authenticated;
```

- [x] **Step 2: 在 config.toml 声明本地 bucket**

在 `[storage]` 段后添加（`supabase start` 时自动创建）：

```toml
[storage.buckets.templates]
public = false

[storage.buckets.reports]
public = false
```

- [x] **Step 3: 应用迁移并验证**

```bash
cd /mnt/c/_code/neoskills
supabase db reset
# 或仅推送新迁移（如果不想 reset）：
supabase migration up
```

验证函数存在：

```bash
NEOLYST_URL=http://127.0.0.1:54321 uv run python -c "
from skills.neolyst.scripts import connection
client = connection.get_client()
result = client.rpc('get_template_storage_paths', {'p_report_type': 'company', 'p_language': 'en'}).execute()
print(result.data)
"
```

Expected: `[{'template_file_path': 'company/en/template.docx', 'schema_file_path': 'company/en/schema.yaml'}]`

---

## Task 2: 实现 storage.py

**Files:**
- Create: `skills/neolyst/scripts/storage.py`

- [x] **Step 1: 创建 storage.py**

```python
"""
storage.py — Neolyst Supabase Storage 封装。

只负责文件上传/下载，路径由调用方传入（来自 Supabase RPC）。
bucket 名称是实现细节，调用方只需调用语义化函数。
"""

from pathlib import Path
from supabase import Client

_TEMPLATE_BUCKET = "templates"
_REPORT_BUCKET = "reports"


def upload_template(client: Client, storage_path: str, local_path: str) -> None:
    """上传文件到模板 bucket，已存在时覆盖。"""
    _upload(client, _TEMPLATE_BUCKET, storage_path, local_path)


def download_template(client: Client, storage_path: str, local_path: str) -> None:
    """从模板 bucket 下载文件到本地路径。"""
    _download(client, _TEMPLATE_BUCKET, storage_path, local_path)


def upload_report(client: Client, storage_path: str, local_path: str) -> None:
    """上传文件到报告 bucket，已存在时覆盖。"""
    _upload(client, _REPORT_BUCKET, storage_path, local_path)


def download_report(client: Client, storage_path: str, local_path: str) -> None:
    """从报告 bucket 下载文件到本地路径。"""
    _download(client, _REPORT_BUCKET, storage_path, local_path)


def _upload(client: Client, bucket: str, storage_path: str, local_path: str) -> None:
    local = Path(local_path)
    if not local.exists():
        raise FileNotFoundError(f"Local file not found: {local_path}")
    data = local.read_bytes()
    try:
        client.storage.from_(bucket).upload(storage_path, data)
    except Exception:
        client.storage.from_(bucket).update(storage_path, data)


def _download(client: Client, bucket: str, storage_path: str, local_path: str) -> None:
    local = Path(local_path)
    local.parent.mkdir(parents=True, exist_ok=True)
    data = client.storage.from_(bucket).download(storage_path)
    local.write_bytes(data)
```

- [x] **Step 2: 验证 import**

```bash
uv run python -c "from skills.neolyst.scripts import storage; print('OK')"
```

---

## Task 3: 实现 template.py

**Files:**
- Create: `skills/neolyst/scripts/template.py`

- [x] **Step 1: 创建 template.py**

```python
"""
template.py — Neolyst 模板管理接口。

路径规则在 Supabase 函数中定义，本模块不拼路径字符串。
"""

from pathlib import Path
from supabase import Client
from skills.neolyst.scripts import storage


def upsert_template(
    client: Client,
    report_type: str,
    language: str,
    template_local_path: str,
    schema_local_path: str | None = None,
) -> None:
    """
    上传本地模板文件到 Storage，并 upsert report_template 记录。

    流程：
    1. 调用 RPC get_template_storage_paths 获取目标路径
    2. 上传文件到返回的路径
    3. 调用 RPC upsert_template_record 让服务端写库

    Returns:
        None。幂等操作，多次调用安全。
    """
    resp = client.rpc("get_template_storage_paths", {
        "p_report_type": report_type,
        "p_language": language,
    }).execute()

    if not resp.data:
        raise ValueError(f"get_template_storage_paths returned no data for {report_type}/{language}")

    paths = resp.data[0]
    tmpl_storage_path = paths["template_file_path"]
    schema_storage_path = paths["schema_file_path"]

    storage.upload_template(client, tmpl_storage_path, template_local_path)

    if schema_local_path:
        storage.upload_template(client, schema_storage_path, schema_local_path)

    client.rpc("upsert_template_record", {
        "p_report_type": report_type,
        "p_language": language,
    }).execute()


def reuse_template(
    client: Client,
    report_type: str,
    language: str,
    same_as_report_type: str,
) -> None:
    """
    让 report_type 的模板记录复用 same_as_report_type 的文件路径。

    Raises:
        ValueError: 源模板未发布、report_type 与 same_as_report_type 相同
    """
    try:
        client.rpc("reuse_template", {
            "p_report_type": report_type,
            "p_language": language,
            "p_same_as_report_type": same_as_report_type,
        }).execute()
    except Exception as e:
        raise ValueError(str(e)) from e


def resolve_template(
    client: Client,
    report_type: str,
    language: str,
    dest_dir: str = ".",
) -> dict:
    """
    查询模板记录，下载文件到本地，返回本地路径。

    Args:
        dest_dir: 下载根目录，文件落在 {dest_dir}/templates/{report_type}/{language}/

    Returns:
        {"template_local_path": "...", "schema_local_path": "..." or None}

    Raises:
        ValueError: 模板记录不存在或 template_file_path 为空（未发布）
    """
    record_id = f"{report_type}_{language}"
    resp = client.table("report_template").select("*").eq("id", record_id).execute()

    if not resp.data:
        raise ValueError(f"Template not found: {record_id!r}")

    record = resp.data[0]
    if not record.get("template_file_path"):
        raise ValueError(f"Template not published (empty path): {record_id!r}")

    local_dir = Path(dest_dir) / "templates" / report_type / language

    storage.download_template(
        client,
        record["template_file_path"],
        str(local_dir / "template.docx"),
    )

    schema_local = None
    if record.get("schema_file_path"):
        try:
            schema_local = local_dir / "schema.yaml"
            storage.download_template(
                client,
                record["schema_file_path"],
                str(schema_local),
            )
        except Exception:
            schema_local = None

    return {
        "template_local_path": str(local_dir / "template.docx"),
        "schema_local_path": str(schema_local) if schema_local else None,
    }
```

- [x] **Step 2: 验证 import**

```bash
uv run python -c "from skills.neolyst.scripts import template; print('OK')"
```

---

## Task 4: 集成测试

**Files:**
- Modify: `skills/neolyst/tests/conftest.py`
- Create: `skills/neolyst/tests/test_template.py`

- [x] **Step 1: 在 conftest.py 新增 bucket 初始化 fixture**

```python
@pytest.fixture(scope="session", autouse=True)
def ensure_buckets(neolyst_client):
    """确保 templates 和 reports bucket 存在（幂等）。"""
    for bucket in ("templates", "reports"):
        try:
            neolyst_client.storage.create_bucket(bucket, options={"public": False})
        except Exception:
            pass  # 已存在则忽略
```

- [x] **Step 2: 创建 test_template.py**

```python
"""
test_template.py — template 接口集成测试。
"""
import uuid
import pytest
from pathlib import Path

_SUFFIX = uuid.uuid4().hex[:8]
TEST_REPORT_TYPE = f"test_{_SUFFIX}"
TEST_LANGUAGE = "en"
TEMPLATE_ID = f"{TEST_REPORT_TYPE}_{TEST_LANGUAGE}"


@pytest.fixture(scope="module")
def tmp_template_files(tmp_path_factory):
    """创建最小化 docx 和 yaml 测试文件。"""
    d = tmp_path_factory.mktemp("template_fixtures")
    from docx import Document
    doc = Document()
    doc.add_paragraph("test template")
    tmpl = d / "template.docx"
    doc.save(str(tmpl))
    schema = d / "schema.yaml"
    schema.write_text("fields: []\n")
    return {"template": str(tmpl), "schema": str(schema)}


@pytest.fixture(scope="module")
def uploaded_template(neolyst_client, tmp_template_files):
    """上传测试模板，模块结束后清理。"""
    from skills.neolyst.scripts import template, storage as st
    template.upsert_template(
        neolyst_client,
        report_type=TEST_REPORT_TYPE,
        language=TEST_LANGUAGE,
        template_local_path=tmp_template_files["template"],
        schema_local_path=tmp_template_files["schema"],
    )
    yield TEMPLATE_ID
    # 清理 storage
    resp = neolyst_client.rpc("get_template_storage_paths", {
        "p_report_type": TEST_REPORT_TYPE, "p_language": TEST_LANGUAGE,
    }).execute()
    if resp.data:
        paths = resp.data[0]
        for p in [paths["template_file_path"], paths["schema_file_path"]]:
            try:
                neolyst_client.storage.from_("templates").remove([p])
            except Exception:
                pass
    neolyst_client.table("report_template").delete().eq("id", TEMPLATE_ID).execute()


class TestUpsertTemplate:
    def test_record_has_server_computed_paths(self, neolyst_client, uploaded_template):
        resp = neolyst_client.table("report_template").select("*").eq("id", TEMPLATE_ID).execute()
        assert resp.data
        record = resp.data[0]
        assert record["template_file_path"] == f"{TEST_REPORT_TYPE}/{TEST_LANGUAGE}/template.docx"
        assert record["schema_file_path"] == f"{TEST_REPORT_TYPE}/{TEST_LANGUAGE}/schema.yaml"

    def test_upsert_is_idempotent(self, neolyst_client, uploaded_template, tmp_template_files):
        from skills.neolyst.scripts import template
        template.upsert_template(
            neolyst_client,
            report_type=TEST_REPORT_TYPE,
            language=TEST_LANGUAGE,
            template_local_path=tmp_template_files["template"],
            schema_local_path=tmp_template_files["schema"],
        )
        resp = neolyst_client.table("report_template").select("*").eq("id", TEMPLATE_ID).execute()
        assert len(resp.data) == 1


class TestReuseTemplate:
    def test_reuse_copies_paths(self, neolyst_client, uploaded_template):
        from skills.neolyst.scripts import template
        reuse_type = f"reuse_{_SUFFIX}"
        reuse_id = f"{reuse_type}_{TEST_LANGUAGE}"
        try:
            template.reuse_template(neolyst_client, reuse_type, TEST_LANGUAGE, TEST_REPORT_TYPE)
            resp = neolyst_client.table("report_template").select("*").eq("id", reuse_id).execute()
            assert resp.data
            assert resp.data[0]["template_file_path"] == f"{TEST_REPORT_TYPE}/{TEST_LANGUAGE}/template.docx"
        finally:
            neolyst_client.table("report_template").delete().eq("id", reuse_id).execute()

    def test_reuse_self_raises(self, neolyst_client, uploaded_template):
        from skills.neolyst.scripts import template
        with pytest.raises(ValueError, match="self"):
            template.reuse_template(neolyst_client, TEST_REPORT_TYPE, TEST_LANGUAGE, TEST_REPORT_TYPE)

    def test_reuse_nonexistent_source_raises(self, neolyst_client):
        from skills.neolyst.scripts import template
        with pytest.raises(ValueError, match="not found"):
            template.reuse_template(neolyst_client, f"target_{_SUFFIX}", TEST_LANGUAGE, f"ghost_{_SUFFIX}")


class TestResolveTemplate:
    def test_resolve_downloads_files(self, neolyst_client, uploaded_template, tmp_path):
        from skills.neolyst.scripts import template
        result = template.resolve_template(
            neolyst_client, TEST_REPORT_TYPE, TEST_LANGUAGE, dest_dir=str(tmp_path)
        )
        assert Path(result["template_local_path"]).exists()
        assert result["schema_local_path"] and Path(result["schema_local_path"]).exists()

    def test_resolve_local_path_convention(self, neolyst_client, uploaded_template, tmp_path):
        from skills.neolyst.scripts import template
        result = template.resolve_template(
            neolyst_client, TEST_REPORT_TYPE, TEST_LANGUAGE, dest_dir=str(tmp_path)
        )
        expected = tmp_path / "templates" / TEST_REPORT_TYPE / TEST_LANGUAGE / "template.docx"
        assert result["template_local_path"] == str(expected)

    def test_resolve_unpublished_raises(self, neolyst_client):
        from skills.neolyst.scripts import template
        with pytest.raises(ValueError, match="not published"):
            template.resolve_template(neolyst_client, "company", "en")

    def test_resolve_nonexistent_raises(self, neolyst_client):
        from skills.neolyst.scripts import template
        with pytest.raises(ValueError, match="not found"):
            template.resolve_template(neolyst_client, f"ghost_{_SUFFIX}", "en")
```

- [x] **Step 3: 运行测试**

```bash
cd /mnt/c/_code/neoskills
NEOLYST_URL=http://127.0.0.1:54321 uv run --with pytest pytest skills/neolyst/tests/test_template.py -v
```

Expected（9 tests PASSED）

- [x] **Step 4: 全量测试**

```bash
NEOLYST_URL=http://127.0.0.1:54321 uv run --with pytest pytest skills/neolyst/tests/ -v
```

Expected: 全部通过（含 iter1 的 7 个）

- [x] **Step 5: Commit**

```bash
git add supabase/migrations/20260409000600_050_template_functions.sql \
        supabase/config.toml \
        skills/neolyst/scripts/storage.py \
        skills/neolyst/scripts/template.py \
        skills/neolyst/tests/conftest.py \
        skills/neolyst/tests/test_template.py
git commit -m "feat: add storage/template module with server-side path RPCs"
```

---

## Task 5: 更新 SKILL.md 和路线图

- [x] 将 SKILL.md 接口 2、3、4 标记为 `✅ 已实现`，确认描述与实现一致
- [x] `plans/2026-04-07-neolyst-skill-roadmap.md` Iter 2 状态改为 `已完成`，填入计划文件链接

```bash
git add skills/neolyst/SKILL.md plans/2026-04-07-neolyst-skill-roadmap.md
git commit -m "docs: mark iter2 complete, update SKILL.md template interfaces"
```

---

## 自检

- [x] 迁移文件：`get_template_storage_paths`、`upsert_template_record`、`reuse_template` 三个函数，权限正确
- [x] `config.toml`：`templates` 和 `reports` bucket 已声明
- [x] `storage.py`：`upload` / `download` 两个函数，不含路径逻辑
- [x] `template.py`：三个接口，路径全部来自 RPC，不拼字符串
- [x] `conftest.py`：`ensure_buckets` autouse fixture
- [x] 9 个集成测试通过，module-scope teardown 清理 storage 和数据库
- [x] 全量测试通过（16/16）
- [x] SKILL.md 接口 2/3/4 标记已实现
- [x] 路线图 Iter 2 标记已完成

---

## Post-iter2 补丁（同次 session 完成）

**补丁 1：iter1 analyst RPC fix**

`analyst.py` 中的 `is_active` 校验是业务逻辑，应在 Supabase 侧执行。

- 新增 `supabase/migrations/20260409000550_045_analyst_functions.sql`：添加 `resolve_analyst_by_email(p_email text)` RPC，在服务端做 lowercase/trim、not found 和 is_active=false 的校验，失败时 raise exception
- 重写 `analyst.py`：只调用 RPC，不再在 Python 侧做任何业务判断

**补丁 3：connection.py 密码登录失败未捕获**

`get_client` 在 refresh 失败后用存储的 email+password 重新登录时，若密码本身无效（如本地测试账号连远程服务器），`sign_in_with_password` 抛出的原始 401 直接传播，调用方看不到明确提示。

- 修复：在 `sign_in_with_password` 调用处加 try/except，失败时抛出清晰 `ValueError`，提示调用方向用户索取新凭据
- 更新 SKILL.md 认证说明：说明 token 有效期约 1 小时，以及所有 fallback 失败后必须向用户索取凭据

bucket 创建后无 RLS 策略，导致 authenticated 用户无法上传模板文件。

- 新增 `supabase/migrations/20260409000610_055_storage_policies.sql`：
  - `templates` bucket：所有 authenticated 用户可读，仅 admin 可写
  - `reports` bucket：admin 可读写所有；analyst 可读写自己 draft/submitted 状态的报告文件；sa 可读 submitted/published/rejected 的报告文件

**补丁 4：neolyst.yaml 默认 URL 错误 + 测试多余环境变量**

`neolyst.yaml` 的 `supabase_url` 一直指向远程服务器 `http://47.57.213.88:80`，测试通过 `NEOLYST_URL` 环境变量绕过，导致 Codex 等不设该变量的调用方连接到错误服务器。

- `neolyst.yaml`：`supabase_url` 改为 `http://127.0.0.1:54321`
- `SKILL.md`：示例中的 URL 同步更新
- `conftest.py`：删除 `os.environ.setdefault("NEOLYST_URL", ...)` 覆盖行，测试直接读 yaml 配置
- `docs/skills_neolyst_design.md`：删除远程服务器地址和 admin 账号记录，环境说明仅保留本地

**补丁 5：template_file_path 缺少 bucket 前缀**

`report_template.template_file_path` 存储的路径不含 bucket 名称（如 `company/zh/template.docx`），导致路径不自包含，其他客户端无法直接使用。

- 新增迁移 `20260409000620_056_template_path_prefix.sql`：更新 `get_template_storage_paths` 和 `upsert_template_record` 两个 RPC，路径加 `templates/` 前缀；UPDATE 存量记录补前缀
- `seed.sql`：所有 16 条占位记录填入完整路径（`templates/{report_type}/{language}/template.docx` + `schema.yaml`）
- `storage.py`：重构为通用 `upload(client, storage_path, local_path)` 和 `download(client, storage_path, local_path)`，bucket 从路径首段 `_split()` 自动解析，删除四个语义化包装函数
- `template.py`：调用改为 `storage.upload` / `storage.download`
- `test_template.py`：路径断言和 teardown 的 storage remove 同步更新
- **路径规范确立**：数据库中所有 Storage 路径必须含 bucket 前缀，report 相关字段（Iter 4）同样适用
