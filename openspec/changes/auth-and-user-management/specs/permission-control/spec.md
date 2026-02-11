# 权限控制规范

## ADDED Requirements

### Requirement: 系统支持三种用户角色

系统 SHALL 支持三种用户角色：Admin（系统管理员）、SA（高级分析师）、Analyst（普通分析师）。

#### Scenario: 角色存储在 Supabase Auth app_metadata

- **WHEN** 创建用户时
- **THEN** 角色信息存储在 Supabase Auth 的 **app_metadata** 中（仅服务端可修改）
- **AND** user_metadata 包含用户可修改的信息：`{"full_name": "John Doe", "avatar_url": "..."}`
- **AND** app_metadata 包含安全相关信息：`{"role": "admin"|"sa"|"analyst", "provider": "email"}`
- **AND** role 字段只存在 app_metadata 中（防止用户自行提升权限）

#### Scenario: JWT token 包含角色信息

- **WHEN** 用户成功登录
- **THEN** Supabase Auth 生成的 JWT token 自动包含 role 信息
- **AND** 后端和 RLS policies 可以直接从 JWT 读取角色

#### Scenario: RLS 辅助函数

系统 SHALL 提供 PostgreSQL 函数从 JWT token 中提取当前用户角色。

**实现：**
```sql
CREATE OR REPLACE FUNCTION get_current_role()
RETURNS VARCHAR AS $$
  SELECT (auth.jwt()->>'app_metadata'->>'role')::VARCHAR;
$$ LANGUAGE sql SECURITY DEFINER;
```

**使用示例：**
```sql
-- 所有认证用户可读
CREATE POLICY "All users can view analysts"
ON analyst FOR SELECT TO authenticated USING (true);

-- 只有 Admin 可写
CREATE POLICY "Only Admin can modify analysts"
ON analyst FOR ALL TO authenticated
USING (get_current_role() = 'admin')
WITH CHECK (get_current_role() = 'admin');
```

---

## 权限矩阵

| 功能 | Admin | SA | Analyst |
|------|-------|------|----------|
| 用户管理 | ✅ | ❌ | ❌ |
| Region 管理 | ✅ | ❌ | ❌ |
| Analyst 信息管理 | ✅ | ❌ | ❌ |
| 查看 Analyst 信息 | ✅ | ✅ | ✅ |
| 查看报告 | ✅ | ✅ | ✅ |
| 审核报告 | ✅ | ✅ | ❌ |

**注意：** SA 和 Analyst 的查看报告和审核报告功能将在后续变更中实现。

---

## API 权限检查

### Requirement: 前端权限检查函数

系统 SHALL 提供前端权限检查函数，用于 UI 层面的显示控制。

**实现：**
```typescript
// composables/usePermission.ts
export function usePermission() {
  const { userState } = useAuth()

  const isAdmin = () => userState.user?.role === 'admin'
  const isSA = () => userState.user?.role === 'sa'
  const canManageUsers = isAdmin
  const canManageRegions = isAdmin
  const canManageAnalystInfo = isAdmin

  const canAccessReportReview = isSA || isAdmin
  const canViewReports = true  // 所有认证用户都可查看

  return {
    isAdmin,
    isSA,
    isAnalyst,
    canManageUsers,
    canManageRegions,
    canManageAnalystInfo,
    canAccessReportReview,
    canViewReports
  }
}
```

---

## 后端权限验证

### Requirement: 后端中间件验证

系统 SHALL 提供 FastAPI 中间件验证用户角色。

**实现：**
```python
# core/security.py
from fastapi import Request, HTTPException
from functools import wraps

def require_role(*allowed_roles: str):
    def decorator(f):
        @wraps(f)
        async def wrapper(request: Request, *args, **kwargs):
            # 从 JWT 提取角色
            token = request.headers.authorization.split(' ')[1]
            payload = jwt.decode(token, options={'verify_signature': False})
            role = payload.get('app_metadata', {}).get('role')

            if role not in allowed_roles:
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions"
                )

            return await f(*args, **kwargs)
        return wrapper
```

**使用示例：**
```python
@app.get("/api/users")
@require_role('admin')
async def get_users(request: Request):
    return {"users": [...]}

@app.post("/api/regions")
@require_role('admin')
async def create_region(request: Request):
    return {"region": "created"}
```

---

## 角色定义

### Admin（系统管理员）
- **完整权限**：可以访问所有功能
- **用户管理**：创建、编辑、删除用户
- **Region 管理**：创建、编辑、删除 Region
- **Analyst 信息管理**：创建、编辑、删除 Analyst 信息
- **报告管理**：完整权限

### SA（Senior Analyst - 高级分析师）
- **有限权限**：可以访问 Analyst 信息和审核功能
- **查看功能**：查看 Analyst 信息列表、查看报告列表
- **审核功能**：审核报告（后续变更）
- **限制**：无法管理用户、Region、Analyst 信息

### Analyst（普通分析师）
- **只读权限**：只能查看数据
- **查看功能**：查看 Analyst 信息列表、查看报告列表
- **限制**：无法管理用户、Region、Analyst 信息
