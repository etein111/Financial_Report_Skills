# RLS 架构设计说明

## 概述

系统采用 **Supabase Auth 原生 JWT** + **数据库 RLS（Row Level Security）** 实现权限控制。

**核心策略**：
- **读操作**：宽松策略，所有认证用户可读（参考数据需要关联查询）
- **写操作**：严格策略，仅 Admin 可写（数据库层 + 应用层双重保护）

**开发端口配置**：
- 前端：`http://localhost:8080`（Vite）
- 后端：`http://localhost:5173`（FastAPI）

---

## 架构

### 认证流程

```
用户登录 → Supabase Auth → 返回原生 JWT → 前端存储
前端请求 → FastAPI 验证 JWT → 提取角色信息 → 执行业务逻辑
```

### 数据库层（RLS）

**辅助函数**：从 JWT 提取用户角色

```sql
CREATE OR REPLACE FUNCTION get_current_role()
RETURNS VARCHAR AS $$
  SELECT CASE
    WHEN auth.jwt()->>'app_metadata'->>'role' IS NOT NULL
    THEN (auth.jwt()->>'app_metadata'->>'role')::VARCHAR
    ELSE 'anonymous'
  END;
$$ LANGUAGE sql SECURITY DEFINER;
```

**策略设计**（以 Region 表为例）：

| 操作 | 策略 | 目的 |
|------|------|------|
| **SELECT** | `USING (true)` | 所有认证用户可读（关联查询需要） |
| **INSERT** | `WITH CHECK (get_current_role() = 'admin')` | 仅 Admin 可创建 |
| **UPDATE** | `USING (get_current_role() = 'admin')` | 仅 Admin 可修改 |
| **DELETE** | `USING (get_current_role() = 'admin')` | 仅 Admin 可删除 |

**为什么读操作宽松？**

参考数据（Region、Analyst 等）需要支持关联查询：
- 填写报告时需要选择 Region
- 创建报告时需要选择 Analyst
- 下拉列表需要显示完整数据

### 应用层（FastAPI）

**依赖函数**：

```python
# backend/src/core/security.py

def get_current_user(credentials) -> dict:
    """验证 JWT 并返回用户信息"""
    token = credentials.credentials
    user_response = supabase_client.auth.get_user(jwt=token)
    return {
        "id": str(user_response.user.id),
        "email": user_response.user.email,
        "role": user_response.user.app_metadata.get("role", "analyst"),
    }

def require_admin(current_user: dict) -> dict:
    """要求当前用户必须是 Admin"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要 Admin 权限")
    return current_user
```

**端点示例**：

```python
# 读操作：所有认证用户可访问
@router.get("")
async def list_regions(
    current_user: Annotated[dict, Depends(get_current_user)]
):
    ...

# 写操作：仅 Admin 可访问
@router.post("")
async def create_region(
    current_user: Annotated[dict, Depends(require_admin)]
):
    ...
```

---

## 安全保证

### 多层防护

```
┌──────────────────────────────────────────────────────┐
│                    安全控制层次                       │
├──────────────────────────────────────────────────────┤
│                                                      │
│  第 1 层：应用层 (FastAPI)                           │
│  ─────────────────────────────────────────────────  │
│  • JWT Token 验证（Supabase 客户端）                 │
│  • require_admin 权限检查                            │
│  • 快速失败，不到达数据库                             │
│                                                      │
│  第 2 层：数据库层 (RLS)                             │
│  ─────────────────────────────────────────────────  │
│  • 写操作：仅 Admin 可执行                           │
│  • 即使绕过 FastAPI 也被阻止                         │
│                                                      │
│  第 3 层：传输层 (HTTPS)                            │
│  ─────────────────────────────────────────────────  │
│  • Supabase Auth JWT 签名验证（ES256）               │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### 权限矩阵

| 数据类型 | 读权限 | 写权限 | 示例表 |
|---------|-------|-------|--------|
| **参考数据** | 所有认证用户 | Admin only | region, analyst |
| **业务数据** | 按角色/行级 | 按角色/行级 | report（未来） |

---

## 维护指南

### 添加新的 API 端点

**只读端点**（所有认证用户可访问）：
```python
@router.get("")
async def list_items(
    current_user: Annotated[dict, Depends(get_current_user)]
):
    ...
```

**写操作端点**（仅 Admin 可访问）：
```python
@router.post("")
async def create_item(
    current_user: Annotated[dict, Depends(require_admin)]
):
    ...
```

### 添加新的参考数据表

参考 `backend/migrations/001_create_region_table.sql` 和 `002_create_analyst_table.sql`：

1. 创建表结构
2. 启用 RLS：`ALTER TABLE xxx ENABLE ROW LEVEL SECURITY;`
3. 创建读策略：`USING (true)`
4. 创建写策略：`get_current_role() = 'admin'`

---

## 参考资料

- [Supabase Auth](https://supabase.com/docs/guides/auth)
- [Supabase RLS](https://supabase.com/docs/guides/auth/row-level-security)
- [PostgREST](https://postgrest.org/en/stable/)
