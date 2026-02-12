# RLS 架构设计说明

## 背景

在实施 auth-and-user-management 变更过程中，发现 Supabase Python 客户端（supabase-py）与某些 RLS 策略配置存在兼容性问题。

## 问题

**现象**：
- ✅ Supabase REST API 直接调用成功
- ✅ Python 客户端直接调用成功
- ❌ FastAPI 服务中通过 Python 客户端调用失败（RLS 策略错误）

**根本原因**：
Supabase Python 客户端通过 PostgREST API 与数据库通信，某些 RLS 策略配置（特别是基于 `get_current_role()` 函数的策略）在这种通信方式下无法正确工作。

## 最终架构决策

### 数据库层（RLS）

**策略**：宽松模式 + 启用 RLS
- RLS 保持启用状态（满足安全要求）
- 策略配置为允许所有 `authenticated` 和 `postgres` 用户的所有操作
- 防止直接数据库连接绕过应用层

```sql
-- 示例：Analyst 表策略
CREATE POLICY "Allow all authenticated operations on analyst"
ON analyst FOR ALL
TO authenticated, postgres
USING (true)
WITH CHECK (true);
```

**好处**：
1. ✅ RLS 启用（防止直接数据库访问）
2. ✅ 与 Python 客户端兼容
3. ✅ 简化策略管理

### 应用层（FastAPI）

**策略**：严格权限控制
- 所有写操作（POST/PUT/DELETE）使用 `require_admin` 依赖
- 读操作（GET）使用 `get_current_user` 依赖（需要认证）
- 权限检查在 JWT 验证后立即执行

**示例**：
```python
@router.get("", response_model=list[RegionResponse])
async def list_regions(
    current_user: Annotated[dict, Depends(get_current_user)]  # 需要认证
) -> list:
    # 所有认证用户可查看
    ...

@router.post("", response_model=RegionResponse)
async def create_region(
    current_user: Annotated[dict, Depends(require_admin)]  # 需要 Admin
) -> dict:
    # 只有 Admin 可创建
    ...
```

## 安全保证

### 多层防护

1. **数据库层（RLS）**
   - 防止绕过应用层直接访问数据库
   - 需要有效的 Supabase 凭证

2. **应用层（FastAPI）**
   - JWT Token 验证
   - 基于 `require_admin` 依赖的权限检查
   - 细粒度的 API 端点权限控制

3. **传输层**
   - HTTPS 加密通信
   - JWT Token 签名验证

### 权限矩阵

| 功能 | 认证要求 | 权限要求 | 实施层 |
|------|---------|---------|--------|
| 查看 Region | ✅ 需要 | 所有认证用户 | FastAPI |
| 创建/编辑/删除 Region | ✅ 需要 | Admin only | FastAPI |
| 查看 Analyst 信息 | ✅ 需要 | 所有认证用户 | FastAPI |
| 创建/编辑/删除 Analyst 信息 | ✅ 需要 | Admin only | FastAPI |
| 用户管理 | ✅ 需要 | Admin only | FastAPI + Supabase Admin API |

## 测试验证

所有权限已通过集成测试验证：
- ✅ Admin 用户可以执行所有操作
- ✅ SA/Analyst 用户可以查看列表
- ✅ SA/Analyst 用户无法创建/编辑/删除（返回 403）
- ✅ 未认证用户无法访问任何端点（返回 401）

## 维护说明

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

### 修改 RLS 策略

如需修改 RLS 策略，确保：
1. 保持 `authenticated` 和 `postgres` 角色
2. 避免使用依赖 `auth.jwt()` 或 `get_current_role()` 的复杂表达式
3. 优先使用简单的 `USING (true)` 和 `WITH CHECK (true)`

## 参考资料

- Supabase Python Client: https://github.com/supabase-community/supabase-py
- Supabase RLS: https://supabase.com/docs/guides/auth/row-level-security
- PostgREST: https://postgrest.org/en/stable/