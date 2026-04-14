# Analyst 模块扩展设计

## 背景

analyst 表比其他字典表（rating、region、sector、report_type）更常用、信息更敏感。
其他字典表不封装专用接口，LLM 直接用 `client.table()` 操作。
analyst 需要独立模块：精确查询返回全量，批量查询返回精简，写入需统一入口。

## 接口

现有 1 个接口扩展为 4 个：

| # | 接口 | 类型 | 说明 |
|---|------|------|------|
| 1 | `resolve_analyst_by_email(client, email)` | 现有 | 精确查一人，返回全字段 |
| 2 | `search_analyst_by_name(client, name)` | 新增 | 模糊查多人，返回精简字段，仅活跃 |
| 3 | `upsert_analyst(client, email, ...)` | 新增 | 以 email 为键创建或更新分析师 |
| 4 | `set_analyst_active(client, email, is_active)` | 新增 | 停用/恢复分析师 |

### 1. resolve_analyst_by_email（不变）

按 email 精确查询一人，返回全字段。
现有实现不变：`client.table("analyst").select("*").eq("email", email_lower)`。

### 2. search_analyst_by_name

```python
def search_analyst_by_name(client: Client, name: str) -> list[dict]:
```

- 同时匹配 `english_name` 和 `chinese_name`（ilike 模糊匹配）
- 只返回 `is_active=True` 的分析师
- 返回字段：`email`、`english_name`、`chinese_name`（不含 sfc、suffix 等）
- `name` 中的 `%` 和 `_` 在 Python 侧 escape，防止通配符注入
- 无匹配时返回空列表，不抛异常

实现方式：PostgREST `or_` + `ilike`

```python
escaped = name.replace("%", "\\%").replace("_", "\\_")
client.table("analyst") \
    .select("email,english_name,chinese_name") \
    .or_(f"english_name.ilike.%{escaped}%,chinese_name.ilike.%{escaped}%") \
    .eq("is_active", True) \
    .execute()
```

### 3. upsert_analyst

```python
def upsert_analyst(
    client: Client,
    email: str,
    english_name: str,
    chinese_name: str | None = None,
    suffix: str | None = None,
    sfc: str | None = None,
    region_code: str | None = None,
    is_active: bool = True,
) -> dict:
```

- 以 `email` 为 upsert 键（`on_conflict="email"`）
- `email` 在 Python 侧做 `strip().lower()`，与 DB CHECK 约束一致
- 返回 upsert 后的完整记录
- DB 触发器 `trg_analyst_updated_at` 自动维护 `updated_at`

### 4. set_analyst_active

```python
def set_analyst_active(client: Client, email: str, is_active: bool) -> dict:
```

- 按email更新 `is_active` 字段
- email 不存在时抛出 `ValueError`
- `email` 在 Python 侧做 `strip().lower()`
- 返回更新后的记录

## 实现位置

所有接口放在 `scripts/analyst.py`，不新增文件。

## SKILL.md 变更

接口表从 1 行扩展为 4 行。新增接口的完整签名和示例追加到 `references/interfaces.md`。

新增"字典表直接操作"章节，说明 rating、region、sector、report_type 不封装接口，LLM 直接用 `client.table()` 操作。

## 约束

- 所有写入操作受 RLS `dict_write` 策略约束，仅 admin 角色可执行
- `email` 字段有 DB CHECK 约束 `email = lower(email)`，Python 侧预先处理
- `region_code` 引用 `region.code`，无外键约束但逻辑上应保证一致性
