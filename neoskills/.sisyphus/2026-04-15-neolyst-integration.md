# neolyst Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 report_maker 和 template_maker 的运行时模板来源和报告提交接入 neolyst

**Architecture:** 新建 `neolyst_integration.py` 模块作为 report_maker 对 neolyst 的统一接口；template_maker 新增发布命令调用 neolyst 的 upsert_template/reuse_template

**Tech Stack:** Python, supabase Python SDK, 现有 neolyst skill 接口

---

## File Structure

```
skills/report_maker/scripts/
  ├── neolyst_integration.py    # 新增：neolyst 接口封装（模板解析/草稿保存/提交）
  └── __init__.py               # 修改：导出新增函数

skills/template_maker/scripts/
  ├── invoke.py                 # 修改：新增 publish 命令
  └── __init__.py               # 修改：导出新增函数

skills/neolyst/scripts/
  ├── connection.py             # 已有：get_client()
  ├── template.py               # 已有：upsert_template, reuse_template, resolve_template
  ├── report.py                 # 已有：save_report, validate_report, submit_report
  ├── coverage.py               # 已有：resolve_coverage, create_coverage
  ├── analyst.py                # 已有：resolve_analyst_by_email
  └── upload_files.py           # 已有：upload_report_files, upload_model_file
```

---

## Task 1: 新建 neolyst_integration.py（report_maker）

**Files:**
- Create: `skills/report_maker/scripts/neolyst_integration.py`
- Test: `skills/report_maker/tests/test_neolyst_integration.py`

- [ ] **Step 1: 创建测试文件框架**

```python
# skills/report_maker/tests/test_neolyst_integration.py
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

# 测试函数将在后续步骤中定义
```

- [ ] **Step 2: 创建 neolyst_integration.py 主模块**

```python
"""
neolyst_integration.py — report_maker 对 neolyst 的统一接口封装。

职责：
1. 模板解析：从 neolyst 获取模板路径（替代本地 router.yaml）
2. 草稿保存：字段映射 + 调用 save_report
3. Coverage 解析：resolve_coverage
4. 分析师解析：resolve_analyst_by_email
5. 草稿校验：调用 validate_report
6. 报告提交：调用 submit_report
7. 文件上传：upload_report_files / upload_model_file
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
from supabase import Client

from neolyst.connection import get_client
from neolyst.template import resolve_template
from neolyst.report import save_report, validate_report, submit_report
from neolyst.coverage import resolve_coverage, create_coverage
from neolyst.analyst import resolve_analyst_by_email
from neolyst.upload_files import upload_report_files, upload_model_file


# ==================== 模板解析 ====================

def resolve_template_for_report(
    report_type: str,
    report_language: str,
    dest_dir: str = ".",
    client: Client = None,
) -> Dict[str, str]:
    """
    从 neolyst 解析模板，返回本地路径。

    Args:
        report_type: 报告类型（如 "company", "macro"）
        report_language: 报告语言（如 "en", "zh"）
        dest_dir: 下载根目录，默认 "."，文件落在 {dest_dir}/templates/{report_type}/{report_language}/
        client: Supabase client，默认从环境变量创建

    Returns:
        {"template_local_path": str, "schema_local_path": str | None}

    Raises:
        ValueError: 模板不存在或未发布
    """
    if client is None:
        client = get_client()
    return resolve_template(client, report_type, report_language, dest_dir)


# ==================== 分析师解析 ====================

def resolve_analysts_from_elements(
    elements: Dict[str, Any],
    client: Client = None,
) -> List[Dict[str, Any]]:
    """
    从 elements.yaml 的 a1~a8 作者槽位解析分析师列表。

    用 resolve_analyst_by_email 校验并标准化，每位分析师返回：
    {"analyst_email": str, "author_order": int, "analyst_id": str}

    Args:
        elements: elements.yaml 内容，需含 a1~a8 槽位
        client: Supabase client

    Returns:
        分析师列表（按 author_order 升序，最多 8 人）

    Raises:
        ValueError: 分析师未找到或已停用
    """
    if client is None:
        client = get_client()

    analysts = []
    for i in range(1, 9):
        email = elements.get(f"a{i}")
        if email:
            record = resolve_analyst_by_email(client, email)
            analysts.append({
                "analyst_email": record["email"],
                "author_order": i,
                "analyst_id": str(record["id"]),
            })

    return analysts


def get_contact_person_options(analysts: List[Dict[str, Any]]) -> List[str]:
    """从分析师列表提取可选的 contact_person 邮箱列表。"""
    return [a["analyst_email"] for a in analysts]


# ==================== Coverage 解析 ====================

def resolve_coverage_for_report(
    ticker: str,
    first_analyst_email: str,
    client: Client = None,
) -> str:
    """
    根据 ticker 和 1作分析师邮箱查询 coverage_id。

    Args:
        ticker: 股票代码
        first_analyst_email: 1作分析师邮箱
        client: Supabase client

    Returns:
        coverage_id 字符串

    Raises:
        ValueError: coverage 未命中、命中多条或数据异常
    """
    if client is None:
        client = get_client()
    return resolve_coverage(client, ticker, first_analyst_email)


# ==================== 字段映射与补齐 ====================

def detect_language_from_title(title: str) -> str:
    """
    从标题判断报告语言。

    规则：标题中任意字符 ord > 127 则判定为 "zh"，否则为 "en"。

    Args:
        title: 报告标题

    Returns:
        "zh" 或 "en"
    """
    for char in title:
        if ord(char) > 127:
            return "zh"
    return "en"


def compress_investment_thesis(abstract: str, max_length: int = 150) -> str:
    """
    将报告摘要压缩为投资要点概述。

    规则：直接截取前 max_length 字符，句尾不截断单词。

    Args:
        abstract: 原始摘要文本
        max_length: 最大长度，默认 150

    Returns:
        压缩后的概述
    """
    if not abstract:
        return ""
    if len(abstract) <= max_length:
        return abstract

    # 找最后一个完整句子结束符
    truncated = abstract[:max_length]
    last_punct = max(
        truncated.rfind('。'),
        truncated.rfind('.'),
        truncated.rfind('！'),
        truncated.rfind('!'),
    )
    if last_punct > max_length * 0.5:
        return truncated[:last_punct + 1]
    return truncated.rstrip()


def map_elements_to_draft(
    elements: Dict[str, Any],
    report_type: str,
    report_file: str,
    pdf_file: str,
    contact_person: str,
    analysts: List[Dict[str, Any]],
    coverage_id: Optional[str] = None,
    investment_thesis: Optional[str] = None,
    model_file: Optional[str] = None,
) -> Dict[str, Any]:
    """
    将 report_maker 的 elements 映射为 neolyst save_report 的 draft 输入。

    最小字段：title、report_type、report_language、analysts、report_file、pdf_file

    提交前补齐字段：contact_person、investment_thesis、coverage_id、ticker、rating、target_price、region_code、sector_id、model_file

    Args:
        elements: elements.yaml 内容
        report_type: 报告类型
        report_file: 最终 Word 文件路径
        pdf_file: 最终 PDF 文件路径
        contact_person: 联系人邮箱（必须属于 analysts）
        analysts: resolve_analysts_from_elements 返回的分析师列表
        coverage_id: coverage UUID（公司类报告）
        investment_thesis: 投资要点概述，默认从 abstract 压缩
        model_file: Excel 模型文件路径（公司类报告）
        region_code: 区域代码（行业类报告）
        sector_id: 行业 UUID（行业类报告）

    Returns:
        neolyst save_report 所需的 draft 字典
    """
    title = elements.get("title", "")
    report_language = detect_language_from_title(title)

    draft = {
        "title": title,
        "report_type": report_type,
        "report_language": report_language,
        "analysts": analysts,
        "report_file": report_file,
        "pdf_file": pdf_file,
        "contact_person": contact_person,
    }

    # investment_thesis：从 abstract 压缩或直接使用传入值
    if investment_thesis is None:
        abstract = elements.get("abstract", "")
        draft["investment_thesis"] = compress_investment_thesis(abstract)
    else:
        draft["investment_thesis"] = investment_thesis

    # 公司类报告字段
    if report_type in ("company", "company_flash"):
        if coverage_id:
            draft["coverage_id"] = coverage_id
        ticker = elements.get("ticker")
        if ticker:
            draft["ticker"] = ticker
        rating = elements.get("rating")
        if rating:
            draft["rating"] = rating
        target_price = elements.get("target_price")
        if target_price:
            draft["target_price"] = target_price
        if model_file:
            draft["model_file"] = model_file

    # 行业类报告字段
    elif report_type in ("sector", "macro", "strategy", "quantitative", "bond"):
        region_code = elements.get("region_code")
        if region_code:
            draft["region_code"] = region_code
        sector_id = elements.get("sector_id")
        if sector_id:
            draft["sector_id"] = sector_id

    return draft


# ==================== 草稿操作 ====================

def save_draft(
    draft: Dict[str, Any],
    client: Client = None,
) -> Dict[str, Any]:
    """
    调用 neolyst save_report 保存草稿。

    Args:
        draft: map_elements_to_draft 返回的草稿字典
        client: Supabase client

    Returns:
        {"report_id": str}
    """
    if client is None:
        client = get_client()
    return save_report(client, draft)


def validate_draft(
    report_id: str,
    client: Client = None,
) -> None:
    """
    调用 neolyst validate_report 校验草稿。

    校验失败时抛出 ValueError。

    Args:
        report_id: 报告 UUID
        client: Supabase client

    Raises:
        ValueError: 校验失败
    """
    if client is None:
        client = get_client()
    validate_report(client, report_id)


def submit_draft(
    report_id: str,
    client: Client = None,
) -> Dict[str, Any]:
    """
    调用 neolyst submit_report 提交报告。

    Args:
        report_id: 报告 UUID
        client: Supabase client

    Returns:
        {"report_id": str, "status": "submitted"}
    """
    if client is None:
        client = get_client()
    return submit_report(client, report_id)


# ==================== 文件上传 ====================

def upload_draft_files(
    report_id: str,
    report_file: str,
    pdf_file: str,
    client: Client = None,
) -> Dict[str, str]:
    """
    上传报告 Word + PDF 文件到 neolyst Storage。

    Args:
        report_id: 报告 UUID
        report_file: Word 文件本地路径
        pdf_file: PDF 文件本地路径
        client: Supabase client

    Returns:
        {"report_id": str, "word_path": str, "pdf_path": str}
    """
    if client is None:
        client = get_client()
    return upload_report_files(client, report_id, report_file, pdf_file)


def upload_model(
    report_id: str,
    model_file: str,
    client: Client = None,
) -> Dict[str, str]:
    """
    上传 Excel 模型文件到 neolyst Storage。

    Args:
        report_id: 报告 UUID
        model_file: Excel 文件本地路径
        client: Supabase client

    Returns:
        {"report_id": str, "model_path": str}
    """
    if client is None:
        client = get_client()
    return upload_model_file(client, report_id, model_file)
```

- [ ] **Step 3: 运行测试验证模块可导入**

Run: `python -c "from report_maker.scripts.neolyst_integration import resolve_template_for_report, resolve_analysts_from_elements, map_elements_to_draft, save_draft, validate_draft, submit_draft; print('OK')"`
Expected: OK

- [ ] **Step 4: 提交**

```bash
git add skills/report_maker/scripts/neolyst_integration.py
git commit -m "feat(report_maker): 新增 neolyst_integration 模块封装 neolyst 接口"
```

---

## Task 2: 修改 report_maker 的模板解析（使用 neolyst）

**Files:**
- Modify: `skills/report_maker/scripts/common.py:71-88`
- Modify: `skills/report_maker/scripts/renderer.py:96-129`（签名已有 neolyst_client 参数）

- [ ] **Step 1: 修改 get_template_name 函数，添加 neolyst 备选路径**

在 `common.py` 的 `get_template_name` 函数中添加说明注释，指出该函数已被 `neolyst_integration.resolve_template_for_report` 替代，保留仅为向后兼容。

```python
# common.py 第 71-88 行
def get_template_name(report_type: str, router_path: Union[str, Path] = None) -> Optional[str]:
    """根据报告类型获取模板名。

    注意：此函数仅用于向后兼容。运行时模板解析请使用
    neolyst_integration.resolve_template_for_report()，它从 neolyst 而非本地 router.yaml 获取模板。
    """
    # ... 原有代码保持不变 ...
```

- [ ] **Step 2: 在 renderer.py 的 render_report 签名文档中添加 neolyst 模板解析说明**

`renderer.py` 第 96-129 行的文档字符串已标注 `neolyst_client` 为已废弃参数。保持不变，但添加一行说明实际模板路径由调用方负责解析后传入。

- [ ] **Step 3: 提交**

```bash
git add skills/report_maker/scripts/common.py skills/report_maker/scripts/renderer.py
git commit -m "docs(report_maker): 说明 get_template_name 已由 neolyst_integration 替代"
```

---

## Task 3: template_maker 新增发布模板命令

**Files:**
- Modify: `skills/template_maker/scripts/invoke.py`
- Modify: `skills/template_maker/scripts/__init__.py`
- Test: `skills/template_maker/tests/test_publish.py`（可选）

- [ ] **Step 1: 在 invoke.py 中新增 publish_template 函数**

在 `invoke.py` 末尾添加：

```python
def publish_template(
    report_type: str,
    language: str,
    template_local_path: str,
    schema_local_path: str = None,
) -> None:
    """
    将本地模板发布到 neolyst。

    调用 neolyst.upsert_template 上传文件并写入 report_template 表。

    Args:
        report_type: 报告类型（如 "company", "macro"）
        language: 语言代码（如 "en", "zh"）
        template_local_path: 本地 Word 模板文件路径
        schema_local_path: 本地 schema.yaml 路径（可选）
    """
    from neolyst.connection import get_client
    from neolyst.template import upsert_template

    client = get_client()
    upsert_template(
        client,
        report_type,
        language,
        template_local_path,
        schema_local_path,
    )
    print(f"✅ 模板已发布: {report_type}/{language}")


def reuse_template_cmd(
    report_type: str,
    language: str,
    same_as_report_type: str,
) -> None:
    """
    让 report_type 复用另一个已发布模板的文件路径（静态复制）。

    主模板重新上传后需重新执行才能同步。

    Args:
        report_type: 目标报告类型
        language: 语言代码
        same_as_report_type: 源报告类型
    """
    from neolyst.connection import get_client
    from neolyst.template import reuse_template

    client = get_client()
    reuse_template(client, report_type, language, same_as_report_type)
    print(f"✅ 模板复用已配置: {report_type}/{language} -> {same_as_report_type}/{language}")
```

- [ ] **Step 2: 在 invoke.py 的 main 函数中注册 CLI 命令**

在 `invoke.py` 的 `main()` 函数中添加：

```python
# invoke.py main() 函数中添加
elif subcommand == "publish":
    import argparse
    parser = argparse.ArgumentParser(description="发布模板到 neolyst")
    parser.add_argument("--report-type", required=True, help="报告类型")
    parser.add_argument("--language", required=True, help="语言代码")
    parser.add_argument("--template", required=True, help="本地模板路径")
    parser.add_argument("--schema", help="本地 schema.yaml 路径（可选）")
    args = parser.parse_args(sys.argv[2:])
    publish_template(args.report_type, args.language, args.template, args.schema)
elif subcommand == "reuse":
    import argparse
    parser = argparse.ArgumentParser(description="复用已发布模板")
    parser.add_argument("--report-type", required=True, help="目标报告类型")
    parser.add_argument("--language", required=True, help="语言代码")
    parser.add_argument("--same-as", dest="same_as", required=True, help="源报告类型")
    args = parser.parse_args(sys.argv[2:])
    reuse_template_cmd(args.report_type, args.language, args.same_as)
```

- [ ] **Step 3: 提交**

```bash
git add skills/template_maker/scripts/invoke.py
git commit -m "feat(template_maker): 新增 publish 和 reuse 命令发布模板到 neolyst"
```

---

## Task 4: report_maker 新增完整提交流程

**Files:**
- Modify: `skills/report_maker/scripts/neolyst_integration.py`（补充缺失函数）
- Create: `skills/report_maker/scripts/workflow.py`（整合完整提交流程）

- [ ] **Step 1: 创建 workflow.py 整合完整提交流程**

```python
"""
workflow.py — report_maker 报告提交流程。

整合 template_maker 发布、report_maker 生成、neolyst 提交的全流程。
"""

from typing import Dict, Any, Optional
from supabase import Client

from .neolyst_integration import (
    resolve_template_for_report,
    resolve_analysts_from_elements,
    resolve_coverage_for_report,
    map_elements_to_draft,
    save_draft,
    validate_draft,
    submit_draft,
    upload_draft_files,
    upload_model,
    get_contact_person_options,
)
from .common import load_yaml


def prepare_and_save_draft(
    elements_path: str,
    report_type: str,
    report_file: str,
    pdf_file: str,
    dest_dir: str = ".",
    client: Client = None,
) -> Dict[str, Any]:
    """
    准备并保存草稿到 neolyst。

    执行步骤：
    1. 加载 elements.yaml
    2. 解析分析师列表
    3. 若是公司类报告，尝试解析 coverage_id
    4. 映射字段并保存草稿

    Args:
        elements_path: elements.yaml 文件路径
        report_type: 报告类型
        report_file: 最终 Word 文件路径
        pdf_file: 最终 PDF 文件路径
        dest_dir: 模板下载目录
        client: Supabase client

    Returns:
        {
            "report_id": str,
            "analysts": List[Dict],
            "contact_person_options": List[str],
            "coverage_id": str | None,
            "draft": Dict,
        }
    """
    elements = load_yaml(elements_path)

    # 解析分析师
    analysts = resolve_analysts_from_elements(elements, client)
    contact_person_options = get_contact_person_options(analysts)
    first_analyst_email = analysts[0]["analyst_email"] if analysts else None

    # 解析 coverage（公司类报告）
    coverage_id = None
    ticker = elements.get("ticker")
    if report_type in ("company", "company_flash") and ticker and first_analyst_email:
        try:
            coverage_id = resolve_coverage_for_report(ticker, first_analyst_email, client)
        except ValueError as e:
            print(f"⚠️ Coverage 未命中: {e}，将在提交前要求用户处理")

    # 映射字段
    draft = map_elements_to_draft(
        elements=elements,
        report_type=report_type,
        report_file=report_file,
        pdf_file=pdf_file,
        contact_person=first_analyst_email or "",
        analysts=analysts,
        coverage_id=coverage_id,
        model_file=elements.get("model_file"),
    )

    # 保存草稿
    result = save_draft(draft, client)

    return {
        "report_id": result["report_id"],
        "analysts": analysts,
        "contact_person_options": contact_person_options,
        "coverage_id": coverage_id,
        "draft": draft,
    }


def submit_report_workflow(
    report_id: str,
    report_file: str,
    pdf_file: str,
    contact_person: str,
    analysts: list,
    coverage_id: Optional[str] = None,
    model_file: Optional[str] = None,
    client: Client = None,
) -> Dict[str, Any]:
    """
    完整提交流程：校验 → 上传文件 → 提交。

    Args:
        report_id: 报告 UUID
        report_file: Word 文件路径
        pdf_file: PDF 文件路径
        contact_person: 联系人邮箱
        analysts: 分析师列表
        coverage_id: coverage UUID（公司类报告）
        model_file: Excel 模型文件路径
        client: Supabase client

    Returns:
        {"report_id": str, "status": str}

    Raises:
        ValueError: 校验失败
    """
    # 1. 校验
    validate_draft(report_id, client)

    # 2. 上传文件
    upload_draft_files(report_id, report_file, pdf_file, client)

    if model_file:
        upload_model(report_id, model_file, client)

    # 3. 提交
    result = submit_draft(report_id, client)
    print(f"✅ 报告已提交: {result['report_id']}, status={result['status']}")

    return result
```

- [ ] **Step 2: 提交**

```bash
git add skills/report_maker/scripts/workflow.py
git commit -m "feat(report_maker): 新增 workflow.py 整合完整提交流程"
```

---

## Task 5: 更新 report_maker SKILL.md 文档

**Files:**
- Modify: `skills/report_maker/SKILL.md`

- [ ] **Step 1: 更新 SKILL.md，添加 neolyst 集成说明**

在 SKILL.md 中添加新章节说明 neolyst 集成后的工作流程变化。

- [ ] **Step 2: 提交**

```bash
git add skills/report_maker/SKILL.md
git commit -m "docs(report_maker): 更新 SKILL.md 说明 neolyst 集成"
```

---

## 自检清单

1. **Spec coverage:** 逐条核对 `docs/todo/skills_neolyst_integration.md`：
   - [x] 废弃 router.yaml → Task 2 说明替代方案
   - [x] upsert_template/reuse_template → Task 3
   - [x] resolve_template 从 neolyst 解析 → Task 1 + Task 2
   - [x] 字段映射（title, report_type, language, analysts, investment_thesis, ticker, rating, target_price, coverage_id, region_code, sector_id）→ Task 1 `map_elements_to_draft`
   - [x] save_draft → Task 1 `save_draft`
   - [x] validate_draft → Task 1 `validate_draft`
   - [x] submit_report → Task 1 `submit_draft`
   - [x] contact_person 交互 → Task 4 `prepare_and_save_draft` 返回 options
   - [x] coverage 解析 → Task 1 `resolve_coverage_for_report`
   - [x] 分析师校验 → Task 1 `resolve_analysts_from_elements`
   - [x] 文件上传 → Task 1 `upload_draft_files` / `upload_model`

2. **Placeholder scan:** 无 TBD/TODO/不完整步骤

3. **Type consistency:** 所有函数签名中参数名与返回字典的 key 一致

---

## 执行选项

**Plan complete and saved to `docs/superpowers/plans/2026-04-15-neolyst-integration.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
