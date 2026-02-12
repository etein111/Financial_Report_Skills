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

#### Scenario: RLS 策略使用 Supabase Auth JWT

- **WHEN** 用户通过 API 访问数据库
- **THEN** RLS 策略直接从 Supabase Auth JWT 读取角色信息
- **AND** 使用 `auth.jwt()->'app_metadata'->>'role'` 提取角色
- **AND** 避免使用自定义函数以确保与 Supabase Python 客户端兼容

**实现：**
```sql
-- 所有认证用户可读
CREATE POLICY "Authenticated users can view analysts"
ON analyst FOR SELECT TO authenticated
USING (true);

-- 只有 Admin 可写
CREATE POLICY "Only Admin can modify analysts"
ON analyst FOR ALL TO authenticated
USING ((auth.jwt()->'app_metadata'->>'role')::text = 'admin')
WITH CHECK ((auth.jwt()->'app_metadata'->>'role')::text = 'admin');
```

---

## 权限矩阵

| 功能 | Admin | SA | Analyst |
|------|-------|------|----------|
| 用户管理 | ✅ | ❌ | ❌ |
| 查看 Region | ✅ | ✅ | ✅ |
| 修改 Region（创建/编辑/删除） | ✅ | ❌ | ❌ |
| 查看 Analyst 信息 | ✅ | ✅ | ✅ |
| 修改 Analyst 信息（创建/编辑/删除） | ✅ | ❌ | ❌ |
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

### Requirement: FastAPI 依赖注入权限验证

系统 SHALL 使用 FastAPI 依赖注入（Dependency Injection）模式验证用户角色。

**实现：**
```python
# core/security.py
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Supabase 客户端（用于验证 token）
supabase_client = get_supabase()
security = HTTPBearer()

def verify_supabase_token(token: str) -> dict:
    """验证 Supabase Auth JWT Token"""
    user_response = supabase_client.auth.get_user(jwt=token)

    if not user_response.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据"
        )

    user = user_response.user
    app_metadata = user.app_metadata or {}

    return {
        "id": str(user.id),
        "email": user.email,
        "role": app_metadata.get("role", "analyst"),
    }

def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> dict:
    """从 Supabase Auth JWT Token 中获取当前用户"""
    token = credentials.credentials
    return verify_supabase_token(token)

def require_admin(
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """要求当前用户必须是 Admin"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要 Admin 权限"
        )
    return current_user
```

**使用示例：**
```python
# 所有认证用户可访问
@router.get("/api/regions")
async def list_regions(
    current_user: Annotated[dict, Depends(get_current_user)]
) -> list:
    # current_user 包含 {id, email, role}
    ...

# 仅 Admin 可访问
@router.post("/api/regions")
async def create_region(
    current_user: Annotated[dict, Depends(require_admin)]
) -> dict:
    # 如果不是 Admin，会自动返回 403
    ...
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
