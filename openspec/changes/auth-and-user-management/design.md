# 认证与权限系统设计文档（FastAPI + Supabase + Jinja2/HTMX）

## 1. Context

本设计对应 `auth-and-user-management` 变更，遵循 proposal 的需求边界，技术方案统一为：

- 服务端：FastAPI 单体
- 平台：Supabase（Auth / Postgres / RLS / Storage）
- 页面层：Jinja2 + HTMX + Tailwind CSS

目标是把权限语义和实现路径收敛到单一事实源，避免前端状态和后端权限漂移。

---

## 2. 设计目标与非目标

### 2.1 目标

- 登录、登出、会话验证、当前用户信息。
- 角色模型：Admin / SA / Analyst。
- Users 管理、Regions 管理、Analyst Info 管理。
- 忘记密码邮件重置与管理员直接改密。
- 登录页、桌面页、管理页、403 页面。

### 2.2 非目标

- 不包含 Coverage/Sector/Template。
- 不包含报告创建/编辑/审核。
- 不实现 refresh token 机制。
- 不实现密码修改审计日志。

---

## 3. 总体架构

```text
Browser
  -> FastAPI (Web + API)
      -> Supabase Auth
      -> Supabase Postgres (RLS)
      -> Supabase Storage
```

架构约束：

- FastAPI 是唯一业务入口。
- 页面访问权限和 API 权限由 FastAPI 统一判断。
- 数据最终权限由 RLS 兜底。

---

## 4. 权限模型（功能权限 vs 数据权限）

### 4.1 角色定义

- Admin：本阶段全部管理权限。
- SA：本阶段不具备管理权限（与 Analyst 一致）。
- Analyst：本阶段不具备管理权限。

### 4.2 功能权限矩阵

| 功能能力 | Admin | SA | Analyst |
|---|---|---|---|
| 登录/登出 | ✅ | ✅ | ✅ |
| 忘记密码（邮件重置） | ✅ | ✅ | ✅ |
| 用户管理（页面与操作） | ✅ | ❌ | ❌ |
| Region 管理（页面与操作） | ✅ | ❌ | ❌ |
| Analyst 信息管理（页面与操作） | ✅ | ❌ | ❌ |
| 管理员改密 | ✅ | ❌ | ❌ |

### 4.3 数据权限矩阵（RLS）

| 数据资源 | SELECT | INSERT | UPDATE | DELETE |
|---|---|---|---|---|
| `region` | 所有已认证用户 | 仅 Admin | 仅 Admin | 仅 Admin |
| `analyst` | 所有已认证用户 | 仅 Admin | 仅 Admin | 仅 Admin |

说明：基础数据“认证可读”不等于开放管理功能页面。

---

## 5. 认证与会话设计

### 5.1 会话策略

- 登录成功后由 FastAPI 写入 HttpOnly Cookie（不使用 localStorage）。
- 所有受保护请求由 FastAPI 从 Cookie 读取 access token。
- token 有效期 24 小时（Supabase 配置）。

### 5.2 关键依赖代码（认证）

```python
from fastapi import HTTPException, Request, status

def get_access_token(request: Request) -> str:
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
```

```python
def get_current_user(token: Annotated[str, Depends(get_access_token)]) -> dict:
    user_res = supabase.auth.get_user(jwt=token)
    user = user_res.user
    if not user:
        raise HTTPException(status_code=401, detail="无效凭据")
    app_meta = user.app_metadata or {}
    user_meta = user.user_metadata or {}
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user_meta.get("full_name"),
        "role": app_meta.get("role", "analyst"),
    }
```

### 5.3 关键依赖代码（角色守卫）

```python
def require_admin(current_user: Annotated[dict, Depends(get_current_user)]) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="No permission")
    return current_user
```

---

## 6. 数据模型与 RLS 设计

### 6.1 核心数据结构

- `region`：地区字典（`name`/`code` 唯一）。
- `analyst`：业务分析师信息（`email` 唯一，`region_id` 外键）。

约束要求：

- `analyst.region_id` 外键采用 `ON DELETE SET NULL`。
- 删除 Region 时不做业务阻断。

Region 预置数据：

- China、Hong Kong、Japan、Taiwan、Korea、India、Macau、US。

### 6.2 RLS 关键策略代码

```sql
alter table region enable row level security;
alter table analyst enable row level security;

create policy "region_select_authenticated"
on region for select to authenticated
using (true);

create policy "region_write_admin"
on region for all to authenticated
using ((auth.jwt()->'app_metadata'->>'role') = 'admin')
with check ((auth.jwt()->'app_metadata'->>'role') = 'admin');

create policy "analyst_select_authenticated"
on analyst for select to authenticated
using (true);

create policy "analyst_write_admin"
on analyst for all to authenticated
using ((auth.jwt()->'app_metadata'->>'role') = 'admin')
with check ((auth.jwt()->'app_metadata'->>'role') = 'admin');
```

### 6.3 数据访问策略（实现边界）

- 不强制引入 ORM。
- 常规读写通过 Supabase 数据访问接口完成。
- 复杂原子动作通过数据库函数（RPC）实现。

---

## 7. 列表与分页（统一规则）

规则：

- 默认按 `created_at DESC`。
- 超过 15 条启用分页。
- 每页固定 15 条。
- 不提供用户自定义每页条数。

关键代码（Region 列表）：

```python
DEFAULT_PAGE_SIZE = 15

@router.get("/api/regions")
async def list_regions(
    page: int = 1,
    current_user: Annotated[dict, Depends(get_current_user)] = None,
):
    page = max(page, 1)
    start = (page - 1) * DEFAULT_PAGE_SIZE
    end = start + DEFAULT_PAGE_SIZE - 1

    res = (
        supabase.table("region")
        .select("*", count="exact")
        .order("created_at", desc=True)
        .range(start, end)
        .execute()
    )
    return {
        "items": res.data,
        "total": res.count or 0,
        "page": page,
        "page_size": DEFAULT_PAGE_SIZE,
    }
```

---

## 8. 页面与路由设计（SSR + HTMX）

### 8.1 页面访问权限

| 路径 | 权限 |
|---|---|
| `/login` | 公开 |
| `/desktop` | 已登录 |
| `/users` | 仅 Admin |
| `/regions` | 仅 Admin |
| `/analyst-info` | 仅 Admin |
| `/403` | 已登录 |

非 Admin 强行访问管理页面时返回 403 页面，文案为 `No permission`。

### 8.2 Desktop-as-Launcher 导航契约

- 桌面页是功能入口（Launcher）。
- 功能卡片统一新标签页打开（`target="_blank"` + `rel="noopener"`）。
- 功能页不提供“返回桌面”按钮；用户通过关闭标签页返回桌面。
- 该契约适用于 Users / Regions / Analyst Info 及后续新增功能页。
- 直接访问功能页时：
  - 未登录：按认证规则处理（跳转登录或返回 401）。
  - 已登录但无权限：返回 403 页面（文案：`No permission`）。

### 8.3 视觉风格与原型对齐

关键代码：

```python
@app.get("/users")
async def users_page(
    request: Request,
    current_user: Annotated[dict, Depends(require_admin)],
):
    return templates.TemplateResponse("users/index.html", {"request": request})
```

- 风格基线：深色背景、简单大气、专业、富有科技感。
- 登录页与桌面页对齐原型：
  - `openspec/changes/auth-and-user-management/01-login-page.jpg`
  - `openspec/changes/auth-and-user-management/02-desktop.jpg`
- 粒子背景与整体氛围为既定设计方向；可调整实现细节，但不得改变视觉方向与信息层级。

---

## 9. API 设计（FastAPI）

### 9.1 认证

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `POST /api/auth/forgot-password`
- 重置密码页面与提交流程使用 Supabase 托管页面，不提供站内 `POST /api/auth/reset-password`

### 9.2 用户管理（Admin）

- `GET /api/users`
- `POST /api/users`
- `PUT /api/users/{id}`
- `PUT /api/users/{id}/password`
- `PUT /api/users/{id}/role`
- `PUT /api/users/{id}/toggle-status`
- `DELETE /api/users/{id}`

### 9.3 Region 管理

- `GET /api/regions`（认证可读）
- `POST /api/regions`（Admin）
- `PUT /api/regions/{id}`（Admin）
- `DELETE /api/regions/{id}`（Admin）

### 9.4 Analyst 信息管理

- `GET /api/analyst-info`（认证可读）
- `POST /api/analyst-info`（Admin）
- `PUT /api/analyst-info/{id}`（Admin）
- `DELETE /api/analyst-info/{id}`（Admin）
- `POST /api/analyst-info/check-email`（Admin）

字段与查询约束（proposal 对齐）：

- 列表搜索字段包含：`full_name`、`chinese_name`、`email`。
- 列表展示字段包含：`full_name`、`chinese_name`、`email`、`region`、`is_active`。
- 创建必填字段：`full_name`、`email`、`region`。

---

## 10. 安全与运维

### 10.1 安全基线

- 角色仅存储在 Auth `app_metadata`（服务端可改）。
- 会话 Cookie 设置 `HttpOnly`、`Secure`、`SameSite=Lax`。
- 忘记密码接口返回统一提示，避免邮箱枚举。

### 10.2 语言与时区约定（proposal 对齐）

- 前端界面语言统一英文（按钮、标题、表单标签、提示文案）。
- 业务数据内容支持中英文。
- 前端展示时间统一使用北京时间（UTC+8）。
- 后端接口与数据库时间约定统一为北京时间（UTC+8）。

### 10.3 调试端点控制

生产环境必须关闭调试端点，开发环境按开关注册：

```python
if settings.DEBUG:
    app.include_router(debug_router, prefix="/debug", tags=["debug"])
```

### 10.4 Supabase 版本与迁移管理（简化）

- 统一使用 Supabase CLI 迁移机制，不自建数据库版本记录表。
- 增量执行依据为 Supabase 内置表 `supabase_migrations.schema_migrations`。
- 所有数据库变更（Schema / SQL 函数 / RLS / Storage 策略）统一放入 `supabase/migrations/*.sql`。
- 命名规范：`YYYYMMDDHHMM_<desc>.sql`。
- 基础数据（如 Region）放 `supabase/seed/regions.sql`，要求幂等。
- 环境策略采用 `dev + prod`，发布顺序固定为：先 `dev`，后 `prod`。
- 不做常态 Dashboard 直改；紧急直改允许，但必须优先接口/脚本，并在当天补齐 migration（回写到 Git）。
- RLS 策略命名不强制版本后缀；仅在权限语义发生重大变化时，建议使用可读版本标识（如 `_v2`）。
- 回滚策略采用前滚修复，不维护复杂回滚脚本。

---

## 11. 一致性修正说明（相对旧设计）

- 去除重复与冲突描述，统一以 proposal 为准。
- 明确“管理页面仅 Admin”与“基础数据认证可读”可以同时成立。
- 明确 Region 删除采用 `ON DELETE SET NULL`，不做关联阻断。
- 明确 403 行为为“返回 403 页面”，不是静默跳转。
- 列表行为统一为 `created_at DESC + 15 条分页`。

该设计可直接作为当前 change 的实现依据。
