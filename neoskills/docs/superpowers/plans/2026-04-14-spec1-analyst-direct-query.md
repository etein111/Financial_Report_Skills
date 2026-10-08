# Spec 1: resolve_analyst_by_email 直接查表 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 resolve_analyst_by_email 从 RPC 改为 Python 侧直接查表，删除废弃 RPC。

**Architecture:** Python 侧用 `client.table("analyst").select("*").eq("email", email_lower)` 直接查询，自行做 lower/trim 和 is_active 校验。SQL 侧通过新迁移删除废弃函数。

**Tech Stack:** Python, Supabase PostgreSQL

---

### Task 1: 修改 analyst.py

**Files:**
- Modify: `skills/neolyst/scripts/analyst.py`

- [ ] **Step 1: 改写函数体**

将 `analyst.py` 改为：

```python
"""
analyst.py — Neolyst analyst 查询模块。

通过 Supabase 表查询获取 analyst 记录，校验逻辑在 Python 侧完成。
"""

from supabase import Client


def resolve_analyst_by_email(client: Client, email: str) -> dict:
    """
    根据邮箱查询并返回 analyst 记录。

    按 analyst 表主键 email 直接查询。is_active 校验在 Python 侧完成。

    Args:
        client: 已认证的 Supabase client
        email: 分析师邮箱（大小写不敏感）

    Returns:
        dict: analyst 记录，含 email, english_name, chinese_name, suffix,
              sfc, region_code, is_active, created_at, updated_at 字段

    Raises:
        ValueError: 找不到对应的 analyst，或 analyst 已停用（is_active=False）
    """
    email_lower = email.strip().lower()
    resp = client.table("analyst").select("*").eq("email", email_lower).execute()
    if not resp.data:
        raise ValueError(f"找不到分析师：{email}")
    record = resp.data[0]
    if not record.get("is_active", True):
        raise ValueError(f"分析师已停用：{email}")
    return record
```

- [ ] **Step 2: 运行现有测试验证**

Run: `uv run pytest skills/neolyst/tests/test_analyst.py -v`
Expected: 4 tests PASS

---

### Task 2: 创建迁移，删除废弃 RPC

**Files:**
- Create: `supabase/migrations/<timestamp>_drop_resolve_analyst_by_email.sql`

- [ ] **Step 1: 用 CLI 创建迁移文件**

Run: `supabase migration new drop_resolve_analyst_by_email`

- [ ] **Step 2: 写入 SQL**

```sql
-- 删除 resolve_analyst_by_email 函数（已改为 Python 侧直接查表）
DROP FUNCTION IF EXISTS public.resolve_analyst_by_email(text);
```

- [ ] **Step 3: 运行迁移验证**

Run: `supabase db reset`
Expected: 无错误

- [ ] **Step 4: 再次运行测试确认全通过**

Run: `uv run pytest skills/neolyst/tests/test_analyst.py -v`
Expected: 4 tests PASS

---

### Task 3: 更新文档

**Files:**
- Modify: `skills/neolyst/SKILL.md`
- Modify: `skills/neolyst/references/interfaces.md`

- [ ] **Step 1: 更新 SKILL.md 接口表格**

接口 #1 的说明改为：`按邮箱查询 analyst 记录（直接查表，非 RPC）`

- [ ] **Step 2: 更新 interfaces.md §1**

描述改为反映直接查表，去掉"内部统一 lowercase"（改为"Python 侧 lowercase"）。

- [ ] **Step 3: 提交**

```bash
git add skills/neolyst/scripts/analyst.py skills/neolyst/SKILL.md skills/neolyst/references/interfaces.md supabase/migrations/
git commit -m "refactor: resolve_analyst_by_email 改为直接查表，删除废弃 RPC"
```
