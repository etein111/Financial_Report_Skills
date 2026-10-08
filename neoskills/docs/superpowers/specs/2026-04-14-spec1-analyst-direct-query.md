# Spec 1: resolve_analyst_by_email 改为直接查表

## 变更

将 `resolve_analyst_by_email` 从 RPC 调用改为 Python 侧直接查 analyst 表。

## Python 侧（scripts/analyst.py）

```python
def resolve_analyst_by_email(client: Client, email: str) -> dict:
    email_lower = email.strip().lower()
    resp = client.table("analyst").select("*").eq("email", email_lower).execute()
    if not resp.data:
        raise ValueError(f"找不到分析师：{email}")
    record = resp.data[0]
    if not record.get("is_active", True):
        raise ValueError(f"分析师已停用：{email}")
    return record
```

- lower/trim、存在性校验、is_active 校验全部在 Python 侧完成
- 函数签名和返回值不变，对调用方无感

## SQL 侧

新迁移中 DROP 函数 `resolve_analyst_by_email` 及其 GRANT。

## 文档更新

- `SKILL.md` 接口表格中模块列从 `analyst` 改为说明"直接查表"
- `references/interfaces.md` §1 更新描述

## 不涉及

- analyst 的 CRUD RPC
- 测试用例（现有测试通过 match 子串匹配，行为不变应直接通过）
