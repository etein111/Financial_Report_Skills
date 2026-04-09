# neolyst Skill 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 `skills/neolyst/` skill，封装所有对 Neolyst Supabase 的业务操作，对外暴露稳定的业务接口。

**Architecture:** 按设计文档 `docs/skills_neolyst_design.md` 中的模块拆分，分为 `connection`、`storage`、`analyst`、`template`、`coverage`、`draft_report`、`validators`、`submit_report` 八个模块，严格保持单向依赖。所有写操作调用 Supabase 侧接口；skill 层负责认证、文件上传和参数整理。测试使用联调环境（`http://47.57.213.88:80`），采用 email+password 实际登录而非 mock。

**Tech Stack:** Python 3.12+, `supabase-py`, `uv`, `pytest`

---

## 文件结构

```
skills/neolyst/
├── SKILL.md
├── scripts/
│   ├── __init__.py
│   ├── connection.py       # 认证、session 管理、Supabase client
│   ├── storage.py          # 文件上传、bucket/路径规则
│   ├── analyst.py          # resolve_analyst_by_email
│   ├── template.py         # resolve_template, upsert_template, reuse_template
│   ├── coverage.py         # resolve_coverage, create_coverage
│   ├── draft_report.py     # save_draft_report
│   ├── validators.py       # validators(report_id, version_no)
│   └── submit_report.py    # submit_report(report_id, version_no)
└── tests/
    ├── __init__.py
    ├── conftest.py          # pytest fixtures：neolyst_dir, client, test data 清理
    ├── test_connection.py
    ├── test_storage.py
    ├── test_analyst.py
    ├── test_template.py
    ├── test_coverage.py
    ├── test_draft_report.py
    ├── test_validators.py
    └── test_submit_report.py
```

**依赖说明（新增到 pyproject.toml）：**
- `supabase>=2.0.0`

**测试环境：**
- URL: `http://47.57.213.88:80`
- Admin: `admin@neolyst.com` / `Admin123`
- `.neolyst` 文件位置：测试时写入 `~/tmp/neolyst_test/.neolyst`

---

## Task 1：项目脚手架与依赖

**Files:**
- Create: `skills/neolyst/SKILL.md`
- Create: `skills/neolyst/scripts/__init__.py`
- Create: `skills/neolyst/tests/__init__.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: 添加 supabase-py 依赖**

编辑 `pyproject.toml`，在 `dependencies` 中添加：

```toml
[project]
dependencies = [
    "docxcompose>=2.1.0",
    "docxtpl>=0.20.0",
    "python-docx==1.1.0",
    "pyyaml==6.0.1",
    "supabase>=2.0.0",
]
```

- [ ] **Step 2: 同步依赖**

```bash
cd /mnt/c/_code/neoskills && uv sync
```

Expected: 输出安装 `supabase` 及其依赖，无报错。

- [ ] **Step 3: 创建目录与空文件**

```bash
mkdir -p skills/neolyst/scripts skills/neolyst/tests
touch skills/neolyst/scripts/__init__.py
touch skills/neolyst/tests/__init__.py
```

- [ ] **Step 4: 调用 skill-creator 创建 SKILL.md**

按 `docs/SKILL_STANDARD.md` 规定，创建 `SKILL.md` 必须通过 `skill-creator`。调用时提供以下上下文：
- skill 名称：`neolyst`
- 触发场景：其他 skill（如 `report_maker`）需要访问 Neolyst Supabase 数据库时
- 对外接口列表：见下方参考内容

参考 `SKILL.md` 内容（供 skill-creator 使用，最终以 skill-creator 输出为准）：

```markdown
---
name: neolyst
description: "Neolyst Supabase 数据操作 skill，封装分析师解析、模板管理、Coverage 管理、draft 保存、校验和提交等业务接口。"
---

# neolyst

Neolyst Supabase 业务操作 skill。

## 登录身份

身份信息读写自 `{cwd}/.neolyst`，格式：
```json
{ "email": "...", "password": "...", "access_token": "...", "refresh_token": "...", "expires_at": 1712345678 }
```

`connection.py` 启动时先尝试用 `access_token`+`refresh_token` 恢复 session；若已过期则用 `email`+`password` 重新登录并回写该文件。

## 对外接口

- `resolve_analyst_by_email(email)` → `analyst_id`
- `resolve_template(report_type, language)` → `{template_local_path, schema_local_path}`
- `upsert_template(report_type, language, name, template_local_path, schema_local_path)` → None
- `reuse_template(report_type, language, same_as_report_type)` → None
- `resolve_coverage(ticker, first_analyst_id)` → `coverage_id`
- `create_coverage(ticker, english_full_name, sector_id, isin, country_of_domicile, analysts, chinese_short_name=None, traditional_chinese=None)` → `coverage_id`
- `save_draft_report(draft_input: dict)` → `{report_id, version_no, status}`
- `validators(report_id, version_no)` → `{report_id, version_no}`
- `submit_report(report_id, version_no)` → `{report_id, status, version_no}`

## Storage Buckets

- 模板 bucket：路径以 `template_file_path` / `schema_file_path` 为准
- 报告 bucket：`{report_id}/{report_id}_{version_no3}_{label}_{ts}.{ext}`
```

- [ ] **Step 5: Commit**

```bash
cd /mnt/c/_code/neoskills
git add pyproject.toml skills/neolyst/
git commit -m "chore: scaffold neolyst skill with supabase dependency"
```

---

## Task 2：connection.py

**Files:**
- Create: `skills/neolyst/scripts/connection.py`
- Create: `skills/neolyst/tests/test_connection.py`

- [ ] **Step 1: 写失败测试**

`skills/neolyst/tests/test_connection.py`：

```python
import json
import os
import pytest
from pathlib import Path

NEOLYST_DIR = Path(os.environ.get("NEOLYST_TEST_DIR", Path.home() / "tmp" / "neolyst_test"))

@pytest.fixture(autouse=True)
def clean_neolyst_file():
    """每个测试前清除 .neolyst 文件"""
    neolyst_file = NEOLYST_DIR / ".neolyst"
    NEOLYST_DIR.mkdir(parents=True, exist_ok=True)
    neolyst_file.unlink(missing_ok=True)
    yield
    # 测试后不清除，方便检查

def test_get_client_with_credentials_writes_session(tmp_path):
    """用 email+password 登录后写入 .neolyst 文件"""
    from skills.neolyst.scripts import connection

    client = connection.get_client(
        neolyst_dir=str(NEOLYST_DIR),
        email="admin@neolyst.com",
        password="Admin123",
    )
    assert client is not None
    neolyst_file = NEOLYST_DIR / ".neolyst"
    assert neolyst_file.exists()
    data = json.loads(neolyst_file.read_text())
    assert data["email"] == "admin@neolyst.com"
    assert "access_token" in data
    assert "refresh_token" in data
    assert "expires_at" in data

def test_get_client_reuses_session(tmp_path):
    """已有有效 session 时不重新登录（access_token 相同）"""
    from skills.neolyst.scripts import connection

    # 先登录写入 session
    client1 = connection.get_client(
        neolyst_dir=str(NEOLYST_DIR),
        email="admin@neolyst.com",
        password="Admin123",
    )
    data1 = json.loads((NEOLYST_DIR / ".neolyst").read_text())
    token1 = data1["access_token"]

    # 再次获取 client，应复用 session
    client2 = connection.get_client(neolyst_dir=str(NEOLYST_DIR))
    data2 = json.loads((NEOLYST_DIR / ".neolyst").read_text())
    assert data2["access_token"] == token1

def test_get_client_no_file_no_credentials_raises():
    """没有 .neolyst 文件也没有传 credentials 时应抛出错误"""
    from skills.neolyst.scripts import connection

    with pytest.raises(Exception, match="credentials"):
        connection.get_client(neolyst_dir=str(NEOLYST_DIR))
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd /mnt/c/_code/neoskills
uv run pytest skills/neolyst/tests/test_connection.py -v 2>&1 | head -30
```

Expected: `ImportError` 或 `ModuleNotFoundError`（connection.py 不存在）。

- [ ] **Step 3: 实现 connection.py**

`skills/neolyst/scripts/connection.py`：

```python
"""
connection.py — Neolyst Supabase 认证与 client 管理。

.neolyst 文件格式：
  { "email": "...", "password": "...", "access_token": "...",
    "refresh_token": "...", "expires_at": 1712345678 }
"""

import json
import time
from pathlib import Path

from supabase import create_client, Client

DEFAULT_SUPABASE_URL = "http://47.57.213.88:80"
NEOLYST_FILE = ".neolyst"
SERVER_URL_OVERRIDE_FILE = ".neolyst.server.url"


def _supabase_url(neolyst_dir: str) -> str:
    override = Path(neolyst_dir) / SERVER_URL_OVERRIDE_FILE
    if override.exists():
        return override.read_text().strip()
    return DEFAULT_SUPABASE_URL


def _load_neolyst(neolyst_dir: str) -> dict | None:
    p = Path(neolyst_dir) / NEOLYST_FILE
    if not p.exists():
        return None
    return json.loads(p.read_text())


def _save_neolyst(neolyst_dir: str, data: dict) -> None:
    p = Path(neolyst_dir) / NEOLYST_FILE
    Path(neolyst_dir).mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))


def _is_expired(expires_at: int, buffer_seconds: int = 60) -> bool:
    return time.time() >= (expires_at - buffer_seconds)


def get_client(
    neolyst_dir: str = ".",
    email: str | None = None,
    password: str | None = None,
) -> Client:
    """
    返回已认证的 Supabase client。

    优先顺序：
    1. 从 .neolyst 恢复 session（refresh 若已过期）
    2. 用传入的 email+password 登录
    3. 若均无，抛出 ValueError

    Args:
        neolyst_dir: .neolyst 文件所在目录（默认当前工作目录）
        email: 可选，仅在无可用 session 时使用
        password: 可选，仅在无可用 session 时使用

    Returns:
        已认证的 supabase Client
    """
    url = _supabase_url(neolyst_dir)
    # supabase-py 需要 anon key；对于本项目使用 service_role 或 anon key
    # anon key 从联调环境获取（硬编码 fallback，可由 .neolyst.anon_key 覆盖）
    anon_key_file = Path(neolyst_dir) / ".neolyst.anon_key"
    if anon_key_file.exists():
        anon_key = anon_key_file.read_text().strip()
    else:
        # 联调环境的默认 anon key
        anon_key = _get_default_anon_key()

    client = create_client(url, anon_key)
    data = _load_neolyst(neolyst_dir)

    if data and data.get("access_token"):
        if not _is_expired(data.get("expires_at", 0)):
            # session 有效，直接恢复
            client.auth.set_session(data["access_token"], data["refresh_token"])
            return client
        else:
            # 尝试 refresh
            try:
                resp = client.auth.refresh_session(data["refresh_token"])
                session = resp.session
                _save_neolyst(neolyst_dir, {
                    "email": data.get("email", ""),
                    "password": data.get("password", ""),
                    "access_token": session.access_token,
                    "refresh_token": session.refresh_token,
                    "expires_at": session.expires_at,
                })
                return client
            except Exception:
                pass  # refresh 失败，继续尝试 password 登录

    # 用 email+password 登录
    _email = email or (data.get("email") if data else None)
    _password = password or (data.get("password") if data else None)
    if not _email or not _password:
        raise ValueError(
            "No valid session found and no credentials provided. "
            "Pass email+password or ensure .neolyst has valid credentials."
        )

    resp = client.auth.sign_in_with_password({"email": _email, "password": _password})
    session = resp.session
    _save_neolyst(neolyst_dir, {
        "email": _email,
        "password": _password,
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "expires_at": session.expires_at,
    })
    return client


def _get_default_anon_key() -> str:
    """联调环境的 anon key（从 Supabase 项目设置获取）。"""
    # 这个值在首次部署时从 Supabase dashboard 获取
    # 如果不知道，可以通过 http://47.57.213.88:80 的 admin API 获取
    return "***REMOVED-JWT***"
```

- [ ] **Step 4: 运行测试**

```bash
cd /mnt/c/_code/neoskills
uv run pytest skills/neolyst/tests/test_connection.py -v
```

Expected: 3 tests PASS（需要联调环境可达）。若 anon_key 不对，先通过 Supabase admin API 获取正确的 anon key 并更新 `_get_default_anon_key()`。

- [ ] **Step 5: Commit**

```bash
git add skills/neolyst/scripts/connection.py skills/neolyst/tests/test_connection.py
git commit -m "feat: implement neolyst connection module with session management"
```

---

## Task 3：storage.py

**Files:**
- Create: `skills/neolyst/scripts/storage.py`
- Create: `skills/neolyst/tests/test_storage.py`

设计文档约定：
- 模板 bucket：路径由外部传入（`template_file_path`/`schema_file_path`），不推导
- 报告 bucket：`{report_id}/{report_id}_{version_no3}_{label}_{ts}.{ext}`

Bucket 名称需在测试前从联调环境确认；以下用 `templates` 和 `reports` 作为占位名，实现时从环境变量或常量读取。

- [ ] **Step 1: 写失败测试**

`skills/neolyst/tests/test_storage.py`：

```python
import os
import tempfile
from pathlib import Path
import pytest

NEOLYST_DIR = Path(os.environ.get("NEOLYST_TEST_DIR", Path.home() / "tmp" / "neolyst_test"))

@pytest.fixture
def client():
    from skills.neolyst.scripts.connection import get_client
    return get_client(
        neolyst_dir=str(NEOLYST_DIR),
        email="admin@neolyst.com",
        password="Admin123",
    )

def test_generate_report_file_path():
    """报告文件路径生成规则"""
    from skills.neolyst.scripts.storage import report_file_path

    path = report_file_path(
        report_id="abc-123",
        version_no=2,
        label="report",
        ext="docx",
    )
    # 格式：{report_id}/{report_id}_{version_no3}_{label}_{ts}.{ext}
    assert path.startswith("abc-123/abc-123_002_report_")
    assert path.endswith(".docx")

def test_upload_and_download_template(client, tmp_path):
    """上传模板文件到模板 bucket，再下载到本地"""
    from skills.neolyst.scripts.storage import upload_file, download_file, TEMPLATE_BUCKET

    # 创建测试文件
    src = tmp_path / "test_template.docx"
    src.write_bytes(b"fake docx content for test")

    remote_path = "test/neolyst_test_template.docx"
    upload_file(client, TEMPLATE_BUCKET, str(src), remote_path)

    dst = tmp_path / "downloaded.docx"
    download_file(client, TEMPLATE_BUCKET, remote_path, str(dst))
    assert dst.read_bytes() == b"fake docx content for test"

def test_upload_report_file(client, tmp_path):
    """上传报告文件到报告 bucket"""
    from skills.neolyst.scripts.storage import upload_report_file, REPORT_BUCKET
    import uuid

    report_id = str(uuid.uuid4())
    src = tmp_path / "report.docx"
    src.write_bytes(b"fake report content")

    remote_path = upload_report_file(
        client, report_id=report_id, version_no=1, label="report",
        local_path=str(src), ext="docx"
    )
    assert remote_path.startswith(f"{report_id}/")
    assert "_001_report_" in remote_path
    assert remote_path.endswith(".docx")
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
cd /mnt/c/_code/neoskills
uv run pytest skills/neolyst/tests/test_storage.py -v 2>&1 | head -20
```

Expected: `ImportError`。

- [ ] **Step 3: 实现 storage.py**

`skills/neolyst/scripts/storage.py`：

```python
"""
storage.py — 模板文件和报告文件的 Storage 操作。

Buckets:
- TEMPLATE_BUCKET: 模板资产（路径由外部决定）
- REPORT_BUCKET:   报告版本资产（路径规则：{report_id}/{report_id}_{version_no3}_{label}_{ts}.{ext}）
"""

import time
from datetime import datetime, timezone
from pathlib import Path

from supabase import Client

TEMPLATE_BUCKET = "templates"
REPORT_BUCKET = "reports"


def report_file_path(report_id: str, version_no: int, label: str, ext: str) -> str:
    """生成报告 storage 路径。

    格式：{report_id}/{report_id}_{version_no3}_{label}_{ts}.{ext}
    """
    version_no3 = f"{version_no:03d}"
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{report_id}/{report_id}_{version_no3}_{label}_{ts}.{ext}"


def upload_file(client: Client, bucket: str, local_path: str, remote_path: str) -> None:
    """上传本地文件到指定 bucket 的 remote_path。"""
    data = Path(local_path).read_bytes()
    client.storage.from_(bucket).upload(
        path=remote_path,
        file=data,
        file_options={"upsert": "true"},
    )


def download_file(client: Client, bucket: str, remote_path: str, local_path: str) -> None:
    """从 bucket 下载文件到本地。"""
    data = client.storage.from_(bucket).download(remote_path)
    Path(local_path).parent.mkdir(parents=True, exist_ok=True)
    Path(local_path).write_bytes(data)


def upload_report_file(
    client: Client,
    report_id: str,
    version_no: int,
    label: str,
    local_path: str,
    ext: str,
) -> str:
    """上传报告文件，返回 remote_path。"""
    remote_path = report_file_path(report_id, version_no, label, ext)
    upload_file(client, REPORT_BUCKET, local_path, remote_path)
    return remote_path
```

- [ ] **Step 4: 运行测试**

```bash
cd /mnt/c/_code/neoskills
uv run pytest skills/neolyst/tests/test_storage.py -v
```

Expected: 3 tests PASS。若 bucket 名不对，更新 `TEMPLATE_BUCKET` / `REPORT_BUCKET` 常量后重试。

- [ ] **Step 5: Commit**

```bash
git add skills/neolyst/scripts/storage.py skills/neolyst/tests/test_storage.py
git commit -m "feat: implement neolyst storage module"
```

---

## Task 4：analyst.py

**Files:**
- Create: `skills/neolyst/scripts/analyst.py`
- Create: `skills/neolyst/tests/test_analyst.py`

- [ ] **Step 1: 写失败测试**

`skills/neolyst/tests/test_analyst.py`：

```python
import os
import pytest
from pathlib import Path

NEOLYST_DIR = Path(os.environ.get("NEOLYST_TEST_DIR", Path.home() / "tmp" / "neolyst_test"))

@pytest.fixture
def client():
    from skills.neolyst.scripts.connection import get_client
    return get_client(
        neolyst_dir=str(NEOLYST_DIR),
        email="admin@neolyst.com",
        password="Admin123",
    )

def test_resolve_analyst_by_email_found(client):
    """能根据 email 返回 analyst_id（联调环境中必须存在该 analyst）"""
    from skills.neolyst.scripts.analyst import resolve_analyst_by_email

    # 使用联调环境已有的 analyst email
    analyst_id = resolve_analyst_by_email(client, "admin@neolyst.com")
    assert analyst_id is not None
    assert len(analyst_id) == 36  # UUID 格式

def test_resolve_analyst_by_email_not_found(client):
    """不存在的 email 应抛出具体错误"""
    from skills.neolyst.scripts.analyst import resolve_analyst_by_email

    with pytest.raises(ValueError, match="not found"):
        resolve_analyst_by_email(client, "nonexistent_xxx@example.com")
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
uv run pytest skills/neolyst/tests/test_analyst.py -v 2>&1 | head -20
```

Expected: `ImportError`。

- [ ] **Step 3: 实现 analyst.py**

`skills/neolyst/scripts/analyst.py`：

```python
"""
analyst.py — 分析师身份解析。
"""

from supabase import Client


def resolve_analyst_by_email(client: Client, email: str) -> str:
    """
    根据 email 返回 analyst_id。

    Args:
        client: 已认证的 Supabase client
        email: 分析师邮箱

    Returns:
        analyst_id (str)

    Raises:
        ValueError: analyst 不存在
    """
    resp = (
        client.table("analyst")
        .select("id")
        .eq("email", email)
        .eq("is_active", True)
        .execute()
    )
    rows = resp.data
    if not rows:
        raise ValueError(f"Analyst with email '{email}' not found or inactive.")
    return rows[0]["id"]
```

- [ ] **Step 4: 运行测试**

```bash
uv run pytest skills/neolyst/tests/test_analyst.py -v
```

Expected: 2 tests PASS。若 `admin@neolyst.com` 在 analyst 表中不存在，需先在联调环境创建一条 analyst 记录，或改用已有的 analyst email。

- [ ] **Step 5: Commit**

```bash
git add skills/neolyst/scripts/analyst.py skills/neolyst/tests/test_analyst.py
git commit -m "feat: implement resolve_analyst_by_email"
```

---

## Task 5：template.py

**Files:**
- Create: `skills/neolyst/scripts/template.py`
- Create: `skills/neolyst/tests/test_template.py`

- [ ] **Step 1: 写失败测试**

`skills/neolyst/tests/test_template.py`：

```python
import os
import tempfile
import pytest
from pathlib import Path

NEOLYST_DIR = Path(os.environ.get("NEOLYST_TEST_DIR", Path.home() / "tmp" / "neolyst_test"))

@pytest.fixture
def client():
    from skills.neolyst.scripts.connection import get_client
    return get_client(
        neolyst_dir=str(NEOLYST_DIR),
        email="admin@neolyst.com",
        password="Admin123",
    )

def test_upsert_template_creates_record(client, tmp_path):
    """upsert_template 上传文件后创建/更新 template 记录"""
    from skills.neolyst.scripts.template import upsert_template, resolve_template

    template_file = tmp_path / "template.docx"
    template_file.write_bytes(b"fake docx")
    schema_file = tmp_path / "schema.yaml"
    schema_file.write_text("fields:\n  - title\n")

    upsert_template(
        client,
        report_type="quantitative",
        language="en",
        name="Test Quant Template",
        template_local_path=str(template_file),
        schema_local_path=str(schema_file),
    )

    result = resolve_template(client, report_type="quantitative", language="en", download_dir=str(tmp_path))
    assert Path(result["template_local_path"]).exists()
    assert Path(result["schema_local_path"]).exists()

def test_reuse_template(client, tmp_path):
    """reuse_template 将 same_as_report_type 的路径复制到目标 report_type"""
    from skills.neolyst.scripts.template import reuse_template, resolve_template

    # 先确保 quantitative/en 存在（由上一个测试写入，或单独 setup）
    reuse_template(client, report_type="bond", language="en", same_as_report_type="quantitative")

    result = resolve_template(client, report_type="bond", language="en", download_dir=str(tmp_path))
    quant_result = resolve_template(client, report_type="quantitative", language="en", download_dir=str(tmp_path / "quant"))
    # bond 和 quantitative 应该引用同一 template_file_path
    assert Path(result["template_local_path"]).read_bytes() == Path(quant_result["template_local_path"]).read_bytes()

def test_reuse_template_self_raises(client):
    """不能 reuse 自己"""
    from skills.neolyst.scripts.template import reuse_template

    with pytest.raises(ValueError, match="itself"):
        reuse_template(client, report_type="macro", language="en", same_as_report_type="macro")

def test_reuse_template_missing_source_raises(client):
    """源模板不存在时抛出错误"""
    from skills.neolyst.scripts.template import reuse_template

    with pytest.raises(ValueError, match="not found"):
        reuse_template(client, report_type="bond", language="zh", same_as_report_type="nonexistent_type")
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
uv run pytest skills/neolyst/tests/test_template.py -v 2>&1 | head -20
```

Expected: `ImportError`。

- [ ] **Step 3: 实现 template.py**

`skills/neolyst/scripts/template.py`：

```python
"""
template.py — 模板资产管理。

接口：
- resolve_template: 下载并返回本地模板路径
- upsert_template:  上传文件，写入/更新 template 记录
- reuse_template:   将源 report_type 的路径静态复制到目标记录
"""

from pathlib import Path
from supabase import Client
from .storage import upload_file, download_file, TEMPLATE_BUCKET


def resolve_template(
    client: Client,
    report_type: str,
    language: str,
    download_dir: str,
) -> dict:
    """
    获取 template 记录，下载文件到 download_dir，返回本地路径。

    Returns:
        {"template_local_path": str, "schema_local_path": str}

    Raises:
        ValueError: 模板记录不存在
    """
    row = _fetch_template(client, report_type, language)
    template_local = str(Path(download_dir) / f"template_{report_type}_{language}.docx")
    schema_local = str(Path(download_dir) / f"schema_{report_type}_{language}.yaml")
    download_file(client, TEMPLATE_BUCKET, row["template_file_path"], template_local)
    if row.get("schema_file_path"):
        download_file(client, TEMPLATE_BUCKET, row["schema_file_path"], schema_local)
    return {"template_local_path": template_local, "schema_local_path": schema_local}


def upsert_template(
    client: Client,
    report_type: str,
    language: str,
    name: str,
    template_local_path: str,
    schema_local_path: str,
) -> None:
    """
    上传模板文件到 Storage，写入或更新 template 记录。

    路径规则：templates/{report_type}/{language}/template.docx 和 schema.yaml
    """
    ext = Path(template_local_path).suffix.lstrip(".")
    template_remote = f"{report_type}/{language}/template.{ext}"
    schema_remote = f"{report_type}/{language}/schema.yaml"

    upload_file(client, TEMPLATE_BUCKET, template_local_path, template_remote)
    upload_file(client, TEMPLATE_BUCKET, schema_local_path, schema_remote)

    # upsert template 记录（基于 report_type + language 幂等）
    user_id = client.auth.get_user().user.id
    client.table("template").upsert(
        {
            "name": name,
            "report_type": report_type,
            "language": language,
            "template_file_path": template_remote,
            "schema_file_path": schema_remote,
            "uploaded_by": user_id,
        },
        on_conflict="report_type,language",
    ).execute()


def reuse_template(
    client: Client,
    report_type: str,
    language: str,
    same_as_report_type: str,
) -> None:
    """
    将 same_as_report_type 的 template_file_path/schema_file_path 静态复制到 report_type 记录。

    约束：
    - 源必须存在
    - language 必须相同（同一 language 内复用）
    - report_type 不能等于 same_as_report_type

    Raises:
        ValueError: 约束不满足时
    """
    if report_type == same_as_report_type:
        raise ValueError(f"Cannot reuse template from itself: '{report_type}'")

    source = _fetch_template(client, same_as_report_type, language)

    user_id = client.auth.get_user().user.id
    client.table("template").upsert(
        {
            "report_type": report_type,
            "language": language,
            "name": f"Shared from {same_as_report_type}",
            "template_file_path": source["template_file_path"],
            "schema_file_path": source.get("schema_file_path"),
            "uploaded_by": user_id,
        },
        on_conflict="report_type,language",
    ).execute()


def _fetch_template(client: Client, report_type: str, language: str) -> dict:
    resp = (
        client.table("template")
        .select("*")
        .eq("report_type", report_type)
        .eq("language", language)
        .execute()
    )
    rows = resp.data
    if not rows:
        raise ValueError(
            f"Template not found for report_type='{report_type}', language='{language}'."
        )
    return rows[0]
```

- [ ] **Step 4: 运行测试**

```bash
uv run pytest skills/neolyst/tests/test_template.py -v
```

Expected: 4 tests PASS。若 `upsert` 因表没有 unique constraint 在 `report_type,language` 上失败，改用 select-then-insert/update 方式。

- [ ] **Step 5: Commit**

```bash
git add skills/neolyst/scripts/template.py skills/neolyst/tests/test_template.py
git commit -m "feat: implement template resolve/upsert/reuse"
```

---

## Task 6：coverage.py

**Files:**
- Create: `skills/neolyst/scripts/coverage.py`
- Create: `skills/neolyst/tests/test_coverage.py`

- [ ] **Step 1: 写失败测试**

`skills/neolyst/tests/test_coverage.py`：

```python
import os
import uuid
import pytest
from pathlib import Path

NEOLYST_DIR = Path(os.environ.get("NEOLYST_TEST_DIR", Path.home() / "tmp" / "neolyst_test"))

@pytest.fixture
def client():
    from skills.neolyst.scripts.connection import get_client
    return get_client(
        neolyst_dir=str(NEOLYST_DIR),
        email="admin@neolyst.com",
        password="Admin123",
    )

@pytest.fixture
def analyst_id(client):
    from skills.neolyst.scripts.analyst import resolve_analyst_by_email
    return resolve_analyst_by_email(client, "admin@neolyst.com")

@pytest.fixture
def sector_id(client):
    """获取联调环境的第一个 sector id"""
    resp = client.table("sector").select("id").limit(1).execute()
    return resp.data[0]["id"]

def test_create_and_resolve_coverage(client, analyst_id, sector_id):
    """创建 coverage 后能通过 ticker + analyst_id 解析到"""
    from skills.neolyst.scripts.coverage import create_coverage, resolve_coverage

    ticker = f"TEST{uuid.uuid4().hex[:4].upper()}"
    coverage_id = create_coverage(
        client,
        ticker=ticker,
        english_full_name=f"Test Company {ticker}",
        sector_id=sector_id,
        isin=f"US{uuid.uuid4().hex[:10].upper()}",
        country_of_domicile="US",
        analysts=[{"analyst_id": analyst_id, "role": 1, "sort_order": 1}],
    )
    assert coverage_id is not None

    resolved_id = resolve_coverage(client, ticker=ticker, first_analyst_id=analyst_id)
    assert resolved_id == coverage_id

def test_resolve_coverage_not_found(client, analyst_id):
    """不存在的 ticker 应抛出具体错误"""
    from skills.neolyst.scripts.coverage import resolve_coverage

    with pytest.raises(ValueError, match="not found"):
        resolve_coverage(client, ticker="NOTEXIST_ZZZ999", first_analyst_id=analyst_id)

def test_resolve_coverage_analyst_mismatch(client, sector_id):
    """ticker 存在但 analyst 不在 coverage_analyst 中应抛出错误"""
    from skills.neolyst.scripts.coverage import create_coverage, resolve_coverage
    from skills.neolyst.scripts.analyst import resolve_analyst_by_email

    analyst_id = resolve_analyst_by_email(client, "admin@neolyst.com")
    ticker = f"MISM{uuid.uuid4().hex[:4].upper()}"
    create_coverage(
        client,
        ticker=ticker,
        english_full_name=f"Mismatch Co {ticker}",
        sector_id=sector_id,
        isin=f"US{uuid.uuid4().hex[:10].upper()}",
        country_of_domicile="US",
        analysts=[{"analyst_id": analyst_id, "role": 1, "sort_order": 1}],
    )

    fake_analyst_id = str(uuid.uuid4())
    with pytest.raises(ValueError, match="not found"):
        resolve_coverage(client, ticker=ticker, first_analyst_id=fake_analyst_id)
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
uv run pytest skills/neolyst/tests/test_coverage.py -v 2>&1 | head -20
```

Expected: `ImportError`。

- [ ] **Step 3: 实现 coverage.py**

`skills/neolyst/scripts/coverage.py`：

```python
"""
coverage.py — Coverage 解析与创建。
"""

from supabase import Client


def resolve_coverage(client: Client, ticker: str, first_analyst_id: str) -> str:
    """
    按 ticker 查找候选 coverage，过滤出包含 first_analyst_id 的记录。

    Returns:
        coverage_id (str)

    Raises:
        ValueError: 未命中或命中多条
    """
    # 查询 coverage 和 coverage_analyst 联合
    resp = (
        client.table("coverage")
        .select("id, ticker, coverage_analyst!inner(analyst_id)")
        .eq("ticker", ticker)
        .eq("is_active", True)
        .eq("coverage_analyst.analyst_id", first_analyst_id)
        .execute()
    )
    rows = resp.data
    if not rows:
        raise ValueError(
            f"Coverage not found for ticker='{ticker}' with analyst_id='{first_analyst_id}'."
        )
    if len(rows) > 1:
        ids = [r["id"] for r in rows]
        raise ValueError(
            f"Multiple coverages found for ticker='{ticker}': {ids}. Cannot auto-determine."
        )
    return rows[0]["id"]


def create_coverage(
    client: Client,
    ticker: str,
    english_full_name: str,
    sector_id: str,
    isin: str,
    country_of_domicile: str,
    analysts: list[dict],
    chinese_short_name: str | None = None,
    traditional_chinese: str | None = None,
) -> str:
    """
    创建新 coverage 及初始 coverage_analyst 关系。

    Args:
        analysts: [{"analyst_id": str, "role": int, "sort_order": int}, ...]
                  最多 8 位，必须包含 role=1 的分析师。

    Returns:
        新建的 coverage_id (str)

    Raises:
        ValueError: 创建失败
    """
    if len(analysts) > 8:
        raise ValueError("Coverage supports at most 8 analysts.")
    if not any(a.get("role") == 1 for a in analysts):
        raise ValueError("analysts must include exactly one analyst with role=1.")

    coverage_data = {
        "ticker": ticker,
        "english_full_name": english_full_name,
        "sector_id": sector_id,
        "isin": isin,
        "country_of_domicile": country_of_domicile,
    }
    if chinese_short_name:
        coverage_data["chinese_short_name"] = chinese_short_name
    if traditional_chinese:
        coverage_data["traditional_chinese"] = traditional_chinese

    resp = client.table("coverage").insert(coverage_data).execute()
    rows = resp.data
    if not rows:
        raise ValueError(f"Failed to create coverage for ticker='{ticker}'.")
    coverage_id = rows[0]["id"]

    analyst_rows = [
        {
            "coverage_id": coverage_id,
            "analyst_id": a["analyst_id"],
            "role": a["role"],
            "sort_order": a["sort_order"],
        }
        for a in analysts
    ]
    client.table("coverage_analyst").insert(analyst_rows).execute()
    return coverage_id
```

- [ ] **Step 4: 运行测试**

```bash
uv run pytest skills/neolyst/tests/test_coverage.py -v
```

Expected: 3 tests PASS。

- [ ] **Step 5: Commit**

```bash
git add skills/neolyst/scripts/coverage.py skills/neolyst/tests/test_coverage.py
git commit -m "feat: implement coverage resolve and create"
```

---

## Task 7：draft_report.py

**Files:**
- Create: `skills/neolyst/scripts/draft_report.py`
- Create: `skills/neolyst/tests/test_draft_report.py`

- [ ] **Step 1: 写失败测试**

`skills/neolyst/tests/test_draft_report.py`：

```python
import os
import uuid
import pytest
from pathlib import Path

NEOLYST_DIR = Path(os.environ.get("NEOLYST_TEST_DIR", Path.home() / "tmp" / "neolyst_test"))

@pytest.fixture
def client():
    from skills.neolyst.scripts.connection import get_client
    return get_client(
        neolyst_dir=str(NEOLYST_DIR),
        email="admin@neolyst.com",
        password="Admin123",
    )

@pytest.fixture
def analyst_id(client):
    from skills.neolyst.scripts.analyst import resolve_analyst_by_email
    return resolve_analyst_by_email(client, "admin@neolyst.com")

@pytest.fixture
def coverage_id(client, analyst_id):
    from skills.neolyst.scripts.coverage import create_coverage
    resp = client.table("sector").select("id").limit(1).execute()
    sector_id = resp.data[0]["id"]
    ticker = f"DFT{uuid.uuid4().hex[:4].upper()}"
    return create_coverage(
        client,
        ticker=ticker,
        english_full_name=f"Draft Test Co {ticker}",
        sector_id=sector_id,
        isin=f"US{uuid.uuid4().hex[:10].upper()}",
        country_of_domicile="US",
        analysts=[{"analyst_id": analyst_id, "role": 1, "sort_order": 1}],
    ), ticker

def test_save_draft_report_minimal(client, analyst_id, coverage_id, tmp_path):
    """首次保存 draft，返回 report_id 和 version_no=1"""
    from skills.neolyst.scripts.draft_report import save_draft_report

    cov_id, ticker = coverage_id

    report_file = tmp_path / "report.docx"
    report_file.write_bytes(b"fake report")
    pdf_file = tmp_path / "report.pdf"
    pdf_file.write_bytes(b"fake pdf")

    result = save_draft_report(
        client,
        neolyst_dir=str(NEOLYST_DIR),
        draft={
            "report_id": None,
            "report_type": "company",
            "title": "Test Company Report",
            "coverage_id": cov_id,
            "ticker": ticker,
            "rating": "OUTPERFORM",
            "target_price": 100,
            "report_language": "en",
            "contact_person_id": analyst_id,
            "investment_thesis": "Test thesis.",
            "certificate_confirmed": True,
            "analysts": [{"analyst_id": analyst_id, "role": 1, "sort_order": 1}],
            "report_file": str(report_file),
            "pdf_file": str(pdf_file),
            "model_file": None,
        },
    )
    assert result["report_id"] is not None
    assert result["version_no"] == 1
    assert result["status"] == "draft"

def test_save_draft_report_appends_version(client, analyst_id, coverage_id, tmp_path):
    """对已有 report_id 再次保存，version_no 递增"""
    from skills.neolyst.scripts.draft_report import save_draft_report

    cov_id, ticker = coverage_id
    report_file = tmp_path / "r.docx"
    report_file.write_bytes(b"v1")
    pdf_file = tmp_path / "r.pdf"
    pdf_file.write_bytes(b"v1")

    draft_base = {
        "report_type": "company",
        "title": "Append Version Test",
        "coverage_id": cov_id,
        "ticker": ticker,
        "rating": "OUTPERFORM",
        "target_price": 100,
        "report_language": "en",
        "contact_person_id": analyst_id,
        "investment_thesis": "Thesis.",
        "certificate_confirmed": True,
        "analysts": [{"analyst_id": analyst_id, "role": 1, "sort_order": 1}],
        "report_file": str(report_file),
        "pdf_file": str(pdf_file),
        "model_file": None,
    }

    r1 = save_draft_report(client, neolyst_dir=str(NEOLYST_DIR), draft={**draft_base, "report_id": None})
    report_id = r1["report_id"]

    report_file.write_bytes(b"v2")
    r2 = save_draft_report(client, neolyst_dir=str(NEOLYST_DIR), draft={**draft_base, "report_id": report_id})
    assert r2["report_id"] == report_id
    assert r2["version_no"] == 2
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
uv run pytest skills/neolyst/tests/test_draft_report.py -v 2>&1 | head -20
```

Expected: `ImportError`。

- [ ] **Step 3: 实现 draft_report.py**

`skills/neolyst/scripts/draft_report.py`：

```python
"""
draft_report.py — Draft 报告保存。

职责：文件上传 + 调用 Supabase 接口写入 report/report_version/report_analyst。
"""

import copy
from pathlib import Path

from supabase import Client
from .storage import upload_report_file


def save_draft_report(client: Client, neolyst_dir: str, draft: dict) -> dict:
    """
    保存机器处理结果为 draft 版本。

    Args:
        client: 已认证的 Supabase client
        neolyst_dir: .neolyst 文件所在目录（用于获取当前用户 id）
        draft: 扁平化 draft 输入（见设计文档 3.3 节）

    Returns:
        {"report_id": str, "version_no": int, "status": "draft"}
    """
    user_id = client.auth.get_user().user.id
    report_id = draft.get("report_id")

    # 确定下一个 version_no
    if report_id:
        resp = (
            client.table("report_version")
            .select("version_no")
            .eq("report_id", report_id)
            .order("version_no", desc=True)
            .limit(1)
            .execute()
        )
        version_no = (resp.data[0]["version_no"] + 1) if resp.data else 1
    else:
        version_no = 1

    # 上传文件
    file_paths = {}
    for label, field in [("report", "report_file"), ("pdf", "pdf_file"), ("model", "model_file")]:
        local = draft.get(field)
        if local and Path(local).exists():
            ext = Path(local).suffix.lstrip(".")
            # report_id 在首次保存时还是 None，先用占位符，文件上传后再确定 report_id
            # 因此：先插入 report 记录得到 id，再上传
            file_paths[label] = {"local": local, "ext": ext}

    # 写入 / 更新 report 主表
    report_data = _build_report_data(draft, user_id)
    if report_id:
        client.table("report").update(report_data).eq("id", report_id).execute()
    else:
        resp = client.table("report").insert({**report_data, "owner_user_id": user_id}).execute()
        report_id = resp.data[0]["id"]

    # 上传文件（现在有 report_id 了）
    remote_paths = {}
    for label, info in file_paths.items():
        remote = upload_report_file(
            client,
            report_id=report_id,
            version_no=version_no,
            label=label,
            local_path=info["local"],
            ext=info["ext"],
        )
        remote_paths[label] = remote

    # 写入 report_version
    snapshot = _build_snapshot(draft)
    version_data = {
        "report_id": report_id,
        "version_no": version_no,
        "snapshot_json": snapshot,
        "word_file_path": remote_paths.get("report"),
        "pdf_file_path": remote_paths.get("pdf"),
        "model_file_path": remote_paths.get("model"),
        "changed_by": user_id,
    }
    client.table("report_version").insert(version_data).execute()

    # 更新 report.current_version_no
    client.table("report").update({"current_version_no": version_no}).eq("id", report_id).execute()

    # 刷新 report_analyst
    client.table("report_analyst").delete().eq("report_id", report_id).execute()
    analyst_rows = [
        {
            "report_id": report_id,
            "analyst_id": a["analyst_id"],
            "role": a["role"],
            "sort_order": a["sort_order"],
        }
        for a in (draft.get("analysts") or [])
    ]
    if analyst_rows:
        client.table("report_analyst").insert(analyst_rows).execute()

    return {"report_id": report_id, "version_no": version_no, "status": "draft"}


def _build_report_data(draft: dict, user_id: str) -> dict:
    """从 draft 中提取 report 主表字段。"""
    fields = [
        "title", "report_type", "status", "coverage_id", "sector_id",
        "ticker", "rating", "target_price", "report_language",
        "investment_thesis", "certificate_confirmed", "contact_person_id", "region_code",
    ]
    data = {k: draft[k] for k in fields if k in draft and draft[k] is not None}
    data.setdefault("status", "draft")
    return data


def _build_snapshot(draft: dict) -> dict:
    """构建 snapshot_json，排除本地文件路径字段。"""
    exclude = {"report_file", "pdf_file", "model_file"}
    return {k: v for k, v in draft.items() if k not in exclude}
```

- [ ] **Step 4: 运行测试**

```bash
uv run pytest skills/neolyst/tests/test_draft_report.py -v
```

Expected: 2 tests PASS。

- [ ] **Step 5: Commit**

```bash
git add skills/neolyst/scripts/draft_report.py skills/neolyst/tests/test_draft_report.py
git commit -m "feat: implement save_draft_report"
```

---

## Task 8：validators.py

**Files:**
- Create: `skills/neolyst/scripts/validators.py`
- Create: `skills/neolyst/tests/test_validators.py`

- [ ] **Step 1: 写失败测试**

`skills/neolyst/tests/test_validators.py`：

```python
import os
import uuid
import pytest
from pathlib import Path

NEOLYST_DIR = Path(os.environ.get("NEOLYST_TEST_DIR", Path.home() / "tmp" / "neolyst_test"))

@pytest.fixture
def client():
    from skills.neolyst.scripts.connection import get_client
    return get_client(
        neolyst_dir=str(NEOLYST_DIR),
        email="admin@neolyst.com",
        password="Admin123",
    )

@pytest.fixture
def full_draft(client, tmp_path):
    """创建一个完整的 company draft，返回 (report_id, version_no)"""
    from skills.neolyst.scripts.analyst import resolve_analyst_by_email
    from skills.neolyst.scripts.coverage import create_coverage
    from skills.neolyst.scripts.draft_report import save_draft_report

    analyst_id = resolve_analyst_by_email(client, "admin@neolyst.com")
    resp = client.table("sector").select("id").limit(1).execute()
    sector_id = resp.data[0]["id"]
    ticker = f"VAL{uuid.uuid4().hex[:4].upper()}"
    cov_id = create_coverage(
        client,
        ticker=ticker,
        english_full_name=f"Validators Test Co",
        sector_id=sector_id,
        isin=f"US{uuid.uuid4().hex[:10].upper()}",
        country_of_domicile="US",
        analysts=[{"analyst_id": analyst_id, "role": 1, "sort_order": 1}],
    )
    report_file = tmp_path / "r.docx"
    report_file.write_bytes(b"report")
    pdf_file = tmp_path / "r.pdf"
    pdf_file.write_bytes(b"pdf")
    model_file = tmp_path / "model.xlsx"
    model_file.write_bytes(b"model")

    result = save_draft_report(client, neolyst_dir=str(NEOLYST_DIR), draft={
        "report_id": None,
        "report_type": "company",
        "title": "Validators Test Report",
        "coverage_id": cov_id,
        "ticker": ticker,
        "rating": "OUTPERFORM",
        "target_price": 100,
        "report_language": "en",
        "contact_person_id": analyst_id,
        "investment_thesis": "Thesis.",
        "certificate_confirmed": True,
        "analysts": [{"analyst_id": analyst_id, "role": 1, "sort_order": 1}],
        "report_file": str(report_file),
        "pdf_file": str(pdf_file),
        "model_file": str(model_file),
    })
    return result["report_id"], result["version_no"]

def test_validators_pass(client, full_draft):
    """完整 company draft 应通过校验"""
    from skills.neolyst.scripts.validators import validators

    report_id, version_no = full_draft
    result = validators(client, report_id, version_no)
    assert result["report_id"] == report_id
    assert result["version_no"] == version_no

def test_validators_missing_required_field(client, full_draft):
    """缺少必填字段时校验失败"""
    from skills.neolyst.scripts.validators import validators

    report_id, version_no = full_draft
    # 直接清除 title（模拟缺少必填字段）
    client.table("report").update({"title": None}).eq("id", report_id).execute()

    with pytest.raises(ValueError, match="title"):
        validators(client, report_id, version_no)
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
uv run pytest skills/neolyst/tests/test_validators.py -v 2>&1 | head -20
```

Expected: `ImportError`。

- [ ] **Step 3: 实现 validators.py**

`skills/neolyst/scripts/validators.py`：

```python
"""
validators.py — 提交前校验。

校验范围：见设计文档 3.4 节。
"""

from supabase import Client

REQUIRED_ALWAYS = ["title", "report_type", "report_language", "contact_person_id",
                   "investment_thesis", "certificate_confirmed"]

REQUIRED_BY_TYPE = {
    "company":      ["coverage_id", "ticker", "rating", "target_price"],
    "company_flash": ["coverage_id", "ticker"],
    "sector":       ["region_code", "sector_id"],
    "sector_flash": ["region_code", "sector_id"],
    "macro":        ["region_code"],
    "strategy":     ["region_code"],
    "quantitative": ["region_code"],
    "bond":         ["region_code"],
}

COMPANY_TYPES = {"company", "company_flash"}
MODEL_REQUIRED_TYPES = {"company"}


def validators(client: Client, report_id: str, version_no: int) -> dict:
    """
    校验指定 draft 版本是否满足提交条件。

    Returns:
        {"report_id": str, "version_no": int}

    Raises:
        ValueError: 校验失败，错误信息描述具体问题
    """
    # 1. 获取 report 主表
    report = _fetch_report(client, report_id)

    # 2. 获取 report_version
    version = _fetch_version(client, report_id, version_no)

    # 3. 获取 analysts
    analysts = _fetch_analysts(client, report_id)

    # 4. 结构校验
    _validate_analysts(analysts)

    # 5. 必填字段校验
    _validate_required_fields(report, version)

    # 6. 公司类报告特定校验
    report_type = report["report_type"]
    if report_type in COMPANY_TYPES:
        _validate_company_report(client, report, analysts)

    # 7. model 文件校验
    if report_type in MODEL_REQUIRED_TYPES and not version.get("model_file_path"):
        raise ValueError(f"model_file_path is required for report_type='{report_type}'.")

    return {"report_id": report_id, "version_no": version_no}


def _fetch_report(client: Client, report_id: str) -> dict:
    resp = client.table("report").select("*").eq("id", report_id).execute()
    if not resp.data:
        raise ValueError(f"Report '{report_id}' not found.")
    return resp.data[0]


def _fetch_version(client: Client, report_id: str, version_no: int) -> dict:
    resp = (
        client.table("report_version")
        .select("*")
        .eq("report_id", report_id)
        .eq("version_no", version_no)
        .execute()
    )
    if not resp.data:
        raise ValueError(f"Report version {version_no} not found for report '{report_id}'.")
    return resp.data[0]


def _fetch_analysts(client: Client, report_id: str) -> list[dict]:
    resp = (
        client.table("report_analyst")
        .select("*")
        .eq("report_id", report_id)
        .execute()
    )
    return resp.data


def _validate_analysts(analysts: list[dict]) -> None:
    if not analysts:
        raise ValueError("analysts list is empty.")
    if len(analysts) > 8:
        raise ValueError("analysts list exceeds maximum of 8.")
    role1 = [a for a in analysts if a.get("role") == 1]
    if len(role1) != 1:
        raise ValueError("Exactly one analyst with role=1 is required.")
    sort_orders = [a.get("sort_order") for a in analysts]
    if len(set(sort_orders)) != len(sort_orders):
        raise ValueError("analysts sort_order values must be unique.")


def _validate_required_fields(report: dict, version: dict) -> None:
    for field in REQUIRED_ALWAYS:
        if not report.get(field):
            raise ValueError(f"Required field '{field}' is missing or empty.")
    if report.get("certificate_confirmed") is not True:
        raise ValueError("certificate_confirmed must be true.")

    report_type = report["report_type"]
    for field in REQUIRED_BY_TYPE.get(report_type, []):
        if not report.get(field):
            raise ValueError(f"Required field '{field}' for report_type='{report_type}' is missing.")

    if not version.get("word_file_path"):
        raise ValueError("word_file_path is required (report file not uploaded).")
    if not version.get("pdf_file_path"):
        raise ValueError("pdf_file_path is required (PDF file not uploaded).")


def _validate_company_report(client: Client, report: dict, analysts: list[dict]) -> None:
    coverage_id = report.get("coverage_id")
    ticker = report.get("ticker")

    # coverage 存在性
    resp = client.table("coverage").select("id, ticker").eq("id", coverage_id).execute()
    if not resp.data:
        raise ValueError(f"coverage_id='{coverage_id}' does not exist.")
    coverage = resp.data[0]

    # ticker 一致
    if coverage["ticker"] != ticker:
        raise ValueError(
            f"coverage.ticker='{coverage['ticker']}' does not match report ticker='{ticker}'."
        )

    # 报告 1作 analyst_id 在 coverage_analyst 中
    first_analyst_id = next(a["analyst_id"] for a in analysts if a.get("role") == 1)
    ca_resp = (
        client.table("coverage_analyst")
        .select("id")
        .eq("coverage_id", coverage_id)
        .eq("analyst_id", first_analyst_id)
        .execute()
    )
    if not ca_resp.data:
        raise ValueError(
            f"First analyst '{first_analyst_id}' is not in coverage_analyst for coverage '{coverage_id}'."
        )
```

- [ ] **Step 4: 运行测试**

```bash
uv run pytest skills/neolyst/tests/test_validators.py -v
```

Expected: 2 tests PASS。

- [ ] **Step 5: Commit**

```bash
git add skills/neolyst/scripts/validators.py skills/neolyst/tests/test_validators.py
git commit -m "feat: implement validators for draft submission check"
```

---

## Task 9：submit_report.py

**Files:**
- Create: `skills/neolyst/scripts/submit_report.py`
- Create: `skills/neolyst/tests/test_submit_report.py`

- [ ] **Step 1: 写失败测试**

`skills/neolyst/tests/test_submit_report.py`：

```python
import os
import uuid
import pytest
from pathlib import Path

NEOLYST_DIR = Path(os.environ.get("NEOLYST_TEST_DIR", Path.home() / "tmp" / "neolyst_test"))

@pytest.fixture
def client():
    from skills.neolyst.scripts.connection import get_client
    return get_client(
        neolyst_dir=str(NEOLYST_DIR),
        email="admin@neolyst.com",
        password="Admin123",
    )

@pytest.fixture
def ready_draft(client, tmp_path):
    """创建一个通过 validators 的 draft"""
    from skills.neolyst.scripts.analyst import resolve_analyst_by_email
    from skills.neolyst.scripts.coverage import create_coverage
    from skills.neolyst.scripts.draft_report import save_draft_report

    analyst_id = resolve_analyst_by_email(client, "admin@neolyst.com")
    resp = client.table("sector").select("id").limit(1).execute()
    sector_id = resp.data[0]["id"]
    ticker = f"SUB{uuid.uuid4().hex[:4].upper()}"
    cov_id = create_coverage(
        client,
        ticker=ticker,
        english_full_name=f"Submit Test Co",
        sector_id=sector_id,
        isin=f"US{uuid.uuid4().hex[:10].upper()}",
        country_of_domicile="US",
        analysts=[{"analyst_id": analyst_id, "role": 1, "sort_order": 1}],
    )
    for fname in ["r.docx", "r.pdf", "model.xlsx"]:
        (tmp_path / fname).write_bytes(b"content")

    result = save_draft_report(client, neolyst_dir=str(NEOLYST_DIR), draft={
        "report_id": None,
        "report_type": "company",
        "title": "Submit Test",
        "coverage_id": cov_id,
        "ticker": ticker,
        "rating": "OUTPERFORM",
        "target_price": 100,
        "report_language": "en",
        "contact_person_id": analyst_id,
        "investment_thesis": "Thesis.",
        "certificate_confirmed": True,
        "analysts": [{"analyst_id": analyst_id, "role": 1, "sort_order": 1}],
        "report_file": str(tmp_path / "r.docx"),
        "pdf_file": str(tmp_path / "r.pdf"),
        "model_file": str(tmp_path / "model.xlsx"),
    })
    return result["report_id"], result["version_no"]

def test_submit_report_success(client, ready_draft):
    """提交后 status 变为 submitted"""
    from skills.neolyst.scripts.submit_report import submit_report

    report_id, version_no = ready_draft
    result = submit_report(client, report_id, version_no)
    assert result["status"] == "submitted"
    assert result["report_id"] == report_id
    assert result["version_no"] == version_no

    # 验证数据库状态
    resp = client.table("report").select("status").eq("id", report_id).execute()
    assert resp.data[0]["status"] == "submitted"

def test_submit_report_invalid_version(client):
    """不存在的 report_id 应抛出错误"""
    from skills.neolyst.scripts.submit_report import submit_report

    with pytest.raises(ValueError):
        submit_report(client, str(uuid.uuid4()), 1)
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
uv run pytest skills/neolyst/tests/test_submit_report.py -v 2>&1 | head -20
```

Expected: `ImportError`。

- [ ] **Step 3: 实现 submit_report.py**

`skills/neolyst/scripts/submit_report.py`：

```python
"""
submit_report.py — 将已有 draft 提交为 submitted。
"""

from supabase import Client
from .validators import validators


def submit_report(client: Client, report_id: str, version_no: int) -> dict:
    """
    提交指定 draft 版本。执行前再次校验，通过后推进状态到 submitted。

    Returns:
        {"report_id": str, "status": "submitted", "version_no": int}

    Raises:
        ValueError: 校验失败或提交失败
    """
    # 再次校验
    validators(client, report_id, version_no)

    # 获取当前 report
    resp = client.table("report").select("status, owner_user_id").eq("id", report_id).execute()
    if not resp.data:
        raise ValueError(f"Report '{report_id}' not found.")
    report = resp.data[0]
    from_status = report["status"]

    user_id = client.auth.get_user().user.id

    # 写状态日志
    client.table("report_status_log").insert({
        "report_id": report_id,
        "from_status": from_status,
        "to_status": "submitted",
        "action_by": user_id,
        "version_no": version_no,
    }).execute()

    # 更新 report 状态
    client.table("report").update({"status": "submitted"}).eq("id", report_id).execute()

    return {"report_id": report_id, "status": "submitted", "version_no": version_no}
```

- [ ] **Step 4: 运行测试**

```bash
uv run pytest skills/neolyst/tests/test_submit_report.py -v
```

Expected: 2 tests PASS。

- [ ] **Step 5: Commit**

```bash
git add skills/neolyst/scripts/submit_report.py skills/neolyst/tests/test_submit_report.py
git commit -m "feat: implement submit_report"
```

---

## Task 10：全量测试与最终收尾

**Files:**
- Modify: `skills/neolyst/tests/conftest.py`（可选，如有需要共享的 fixtures）

- [ ] **Step 1: 运行全量测试**

```bash
cd /mnt/c/_code/neoskills
uv run pytest skills/neolyst/tests/ -v --tb=short 2>&1 | tail -30
```

Expected: 所有测试 PASS，无 ERROR。

- [ ] **Step 2: 确认 anon key 正确（如有问题）**

若 Task 2 中 connection 测试因 anon key 失败，通过联调环境的 Supabase 管理页面获取正确的 anon key：

```bash
# 查询联调环境的 project settings
curl -s http://47.57.213.88:80/rest/v1/ -H "apikey: <anon_key>" | head -5
```

更新 `connection.py` 中的 `_get_default_anon_key()` 返回值后重新运行测试。

- [ ] **Step 3: 检查所有模块 import 正常**

```bash
cd /mnt/c/_code/neoskills
uv run python -c "
from skills.neolyst.scripts import connection, storage, analyst, template, coverage, draft_report, validators, submit_report
print('All modules imported OK')
"
```

Expected: 输出 `All modules imported OK`。

- [ ] **Step 4: 最终 commit**

```bash
git add skills/neolyst/
git commit -m "feat: complete neolyst skill implementation and tests"
```

---

## 注意事项

1. **联调环境 anon key**：`connection.py` 中硬编码了 Supabase 默认 demo anon key，如果联调环境不使用默认 key，需在 Task 2 Step 4 时更新。

2. **template 表 unique constraint**：`upsert_template` 使用 `on_conflict="report_type,language"`；若联调环境表上没有该 unique constraint，需改用 select-then-insert/update 方式，或请求在 Supabase 侧添加约束。

3. **`report.title` NOT NULL**：`validators` 测试中直接将 `title` 设为 `null` 可能被数据库约束拒绝，若遇到此问题改为将 `title` 更新为空字符串 `""`，并在 validators 中对空字符串也视为缺失。

4. **测试数据清理**：测试会在联调库中创建 coverage、report 等记录。测试完成后可手动清理，或在 conftest.py 中添加 teardown 钩子按 `ticker` 前缀清理测试数据（`TEST*`、`DFT*`、`VAL*`、`SUB*`、`MISM*`）。
