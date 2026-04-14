# P2 Schema Redesign Phase B Python Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Python 客户端从“保存草稿即创建版本”改成“保存 metadata / 上传文件 / 提交状态”三类独立调用，并移除所有 `version_no/current_version_no/report_version` 客户端假设。

**Architecture:** Python 层继续只做 I/O：组装 payload、调用 RPC、上传 Storage 文件，不做路径规则、状态规则或版本计算。`save_report` 只负责元数据；`upload_report_files` 和 `upload_model_file` 只负责基于 DB 返回的路径前缀上传文件并回写路径；`submit_report` / `retract_report` / `validate_report` 全部对齐 Phase A 的新 RPC 返回。

**Tech Stack:** Python 3、`supabase-py`、项目内 `rpc.py` / `storage.py`、`uv`

---

## File Map

| 路径 | 角色 |
|---|---|
| `skills/neolyst/scripts/save_report.py` | 由 `draft_report.py` 改名而来，只保留 metadata upsert |
| `skills/neolyst/scripts/upload_files.py` | 新增，承载 Word/PDF/Model 上传与路径回写 |
| `skills/neolyst/scripts/submit_report.py` | 改成返回 `{report_id, status}` |
| `skills/neolyst/scripts/retract_report.py` | 改成返回 `{report_id, status}` |
| `skills/neolyst/scripts/validators.py` | 删除对 `report.current_version_no` 的直查，只保留 RPC 调用 |
| `skills/neolyst/scripts/rpc.py` | 只读参考：统一 RPC 调用入口 |
| `skills/neolyst/scripts/storage.py` | 只读参考：Storage 路径必须是 `{bucket}/{path}` |

## Task 1: 将 `draft_report.py` 收口为只保存 metadata 的 `save_report.py`

**Files:**
- Move: `skills/neolyst/scripts/draft_report.py` → `skills/neolyst/scripts/save_report.py`
- Reference: `skills/neolyst/scripts/rpc.py`

- [ ] **Step 1: 重命名模块，避免后续继续沿用旧职责名**

Run:

```bash
git mv skills/neolyst/scripts/draft_report.py skills/neolyst/scripts/save_report.py
```

Expected:

```text
git status 中出现 draft_report.py -> save_report.py 的 rename
```

- [ ] **Step 2: 把 `save_draft_report()` 改成 `save_report()`，删除文件上传和版本提交逻辑**

将 [save_report.py](/mnt/c/_code/neoskills/skills/neolyst/scripts/save_report.py) 改成下面这样：

```python
"""
save_report.py — Neolyst 报告元数据保存接口。

执行流程：
1. 若 report_id 为 None，用 uuid.uuid4() 生成
2. 调用 upsert_report RPC 创建或更新 report 元数据
3. 返回 {"report_id": str}

业务逻辑全部在 Supabase RPC 侧，本模块只做 I/O 和参数整理。
"""

import uuid

from supabase import Client

from . import rpc


FILE_KEYS = ("report_file", "pdf_file", "model_file")


def save_report(client: Client, draft: dict) -> dict:
    """
    创建或更新 report 元数据。

    Args:
        client: 已认证的 Supabase client
        draft: 报告元数据字典；允许带 report_id，文件字段会被剥离

    Returns:
        dict: {"report_id": str}
    """
    report_id = draft.get("report_id") or str(uuid.uuid4())

    payload = {
        key: value
        for key, value in draft.items()
        if key not in FILE_KEYS
    }
    payload["report_id"] = report_id

    row = rpc.single_row(
        rpc.call_rpc(client, "upsert_report", {"p_draft": payload}),
        "upsert_report RPC returned empty data",
    )
    return {"report_id": str(row["report_id"])}
```

- [ ] **Step 3: 搜索仓内脚本目录，确认 Phase B 源码不再引用旧函数名**

Run:

```bash
rg -n "save_draft_report|init_draft_report|commit_draft_version" skills/neolyst/scripts
```

Expected:

```text
不再命中 save_report.py 的实现体；若仍有命中，只允许出现在后续待改模块或文档里
```

## Task 2: 新增 `upload_files.py`，拆出 Word/PDF 和 Model 上传

**Files:**
- Create: `skills/neolyst/scripts/upload_files.py`
- Reference: `skills/neolyst/scripts/rpc.py`
- Reference: `skills/neolyst/scripts/storage.py`

- [ ] **Step 1: 新建 `upload_files.py`，实现共享上传前缀和路径拼接**

新文件内容直接写成下面这样：

```python
"""
upload_files.py — Neolyst 报告文件上传接口。

业务逻辑全部在 Supabase RPC 侧，本模块只负责：
1. 向 generate_upload_path 申请路径前缀
2. 上传本地文件到 Storage
3. 调用 update_report_doc_paths / update_model_path 回写 report 当前路径
"""

from pathlib import Path

from supabase import Client

from . import rpc, storage


def _join_prefix(prefix: str, local_path: str) -> str:
    if not prefix.endswith("/"):
        raise ValueError(f"Invalid upload prefix: {prefix!r}")
    return f"{prefix}{Path(local_path).name}"


def _generate_prefix(client: Client, report_id: str, category: str) -> str:
    row = rpc.single_row(
        rpc.call_rpc(client, "generate_upload_path", {
            "p_report_id": report_id,
            "p_file_category": category,
        }),
        "generate_upload_path RPC returned empty data",
    )
    if isinstance(row, dict):
        return row.get("generate_upload_path") or next(iter(row.values()))
    return str(row)


def upload_report_files(
    client: Client,
    report_id: str,
    report_file: str,
    pdf_file: str,
) -> dict:
    """
    上传 Word + PDF，并回写 report.word_path/report.pdf_path。
    """
    prefix = _generate_prefix(client, report_id, "report")
    word_path = _join_prefix(prefix, report_file)
    pdf_path = _join_prefix(prefix, pdf_file)

    storage.upload(client, word_path, report_file)
    storage.upload(client, pdf_path, pdf_file)

    rpc.call_rpc(client, "update_report_doc_paths", {
        "p_report_id": report_id,
        "p_word_path": word_path,
        "p_pdf_path": pdf_path,
    })

    return {
        "report_id": report_id,
        "word_path": word_path,
        "pdf_path": pdf_path,
    }


def upload_model_file(client: Client, report_id: str, model_file: str) -> dict:
    """
    上传 Model 文件，并回写 report.model_path。
    """
    prefix = _generate_prefix(client, report_id, "model")
    model_path = _join_prefix(prefix, model_file)

    storage.upload(client, model_path, model_file)
    rpc.call_rpc(client, "update_model_path", {
        "p_report_id": report_id,
        "p_model_path": model_path,
    })

    return {
        "report_id": report_id,
        "model_path": model_path,
    }
```

- [ ] **Step 2: 针对 RPC 标量返回补一个更稳妥的前缀提取**

如果本地验证发现 `generate_upload_path` 的响应是标量列表而不是 dict，把 `_generate_prefix()` 收紧成下面这样：

```python
def _generate_prefix(client: Client, report_id: str, category: str) -> str:
    resp = rpc.call_rpc(client, "generate_upload_path", {
        "p_report_id": report_id,
        "p_file_category": category,
    })
    if not resp.data:
        raise ValueError("generate_upload_path RPC returned empty data")

    first = resp.data[0]
    if isinstance(first, dict):
        return str(first.get("generate_upload_path") or next(iter(first.values())))
    return str(first)
```

- [ ] **Step 3: 搜索脚本层，确认文件路径不再手拼 `v{version_no}`**

Run:

```bash
rg -n "v\\{version_no\\}|current_version_no|commit_draft_version|report_version" skills/neolyst/scripts
```

Expected:

```text
不再命中 upload_files.py / save_report.py / validators.py / submit_report.py / retract_report.py 的实现体
```

## Task 3: 对齐 `submit` / `retract` / `validators` 的新返回值

**Files:**
- Modify: `skills/neolyst/scripts/submit_report.py`
- Modify: `skills/neolyst/scripts/retract_report.py`
- Modify: `skills/neolyst/scripts/validators.py`

- [ ] **Step 1: 更新 `submit_report.py`，删除 `version_no` 透传**

把 [submit_report.py](/mnt/c/_code/neoskills/skills/neolyst/scripts/submit_report.py) 改成下面这样：

```python
"""
submit_report.py — Neolyst 报告提交接口。

流程：
1. 调用 submit_report RPC
2. 返回 {"report_id": str, "status": "submitted"}
"""

from supabase import Client

from . import rpc


def submit_report(client: Client, report_id: str) -> dict:
    row = rpc.single_row(rpc.call_rpc(client, "submit_report", {
        "p_report_id": report_id,
    }))
    return {
        "report_id": str(row["report_id"]),
        "status": row["status"],
    }
```

- [ ] **Step 2: 更新 `retract_report.py`，删除 `version_no` 透传**

把 [retract_report.py](/mnt/c/_code/neoskills/skills/neolyst/scripts/retract_report.py) 改成下面这样：

```python
"""
retract_report.py — Neolyst 报告撤回接口。

流程：
1. 调用 retract_report RPC
2. 返回 {"report_id": str, "status": "draft"}
"""

from supabase import Client

from . import rpc


def retract_report(client: Client, report_id: str) -> dict:
    row = rpc.single_row(rpc.call_rpc(client, "retract_report", {
        "p_report_id": report_id,
    }))
    return {
        "report_id": str(row["report_id"]),
        "status": row["status"],
    }
```

- [ ] **Step 3: 更新 `validators.py`，删掉对 `report.current_version_no` 的客户端查询**

把 [validators.py](/mnt/c/_code/neoskills/skills/neolyst/scripts/validators.py) 改成下面这样：

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
    调用 validate_report RPC，校验报告是否满足提交条件。

    Returns:
        dict: {"report_id": str}
    """
    rpc.call_rpc(client, "validate_report", {"p_report_id": report_id})
    return {"report_id": report_id}
```

## Task 4: 脚本层自检与提交

**Files:**
- Modify: `skills/neolyst/scripts/save_report.py`
- Create: `skills/neolyst/scripts/upload_files.py`
- Modify: `skills/neolyst/scripts/submit_report.py`
- Modify: `skills/neolyst/scripts/retract_report.py`
- Modify: `skills/neolyst/scripts/validators.py`

- [ ] **Step 1: 做一次语法级 smoke test**

Run:

```bash
uv run python -m compileall skills/neolyst/scripts
```

Expected:

```text
Compiling 'skills/neolyst/scripts/...'
```

- [ ] **Step 2: 搜索旧接口残留，确保 Phase B 已经完全切到新命名**

Run:

```bash
rg -n "save_draft_report|draft_report|init_draft_report|commit_draft_version|version_no|current_version_no" skills/neolyst/scripts
```

Expected:

```text
只允许命中历史注释或 Phase C 还未处理的测试/文档；脚本实现体不再依赖旧版本模型
```

- [ ] **Step 3: 提交 Python 客户端重构**

Run:

```bash
git add skills/neolyst/scripts/save_report.py skills/neolyst/scripts/upload_files.py skills/neolyst/scripts/submit_report.py skills/neolyst/scripts/retract_report.py skills/neolyst/scripts/validators.py
git commit -m "refactor: split report save and upload flows"
```

Expected:

```text
成功创建只包含 Phase B Python 客户端改动的提交
```
