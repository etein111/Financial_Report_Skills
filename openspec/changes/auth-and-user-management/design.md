# 认证与权限系统设计文档（重构版）

## Context

当前变更 `auth-and-user-management` 的业务目标不变：

- 认证与会话（登录、登出、身份校验）
- 角色权限（Admin / SA / Analyst）
- 用户管理（含管理员改密、启用/禁用）
- Region 管理
- Analyst 信息管理
- 登录页与桌面主页
- 忘记密码与重置密码

本次设计重构只替换技术实现路线，核心原则是：

1. 保持 Supabase 作为数据库/Auth/Storage 平台。
2. 保持 FastAPI 作为唯一服务端业务入口。
3. 取消复杂 SPA 前端状态链路，改为服务端渲染为主（Jinja2 + HTMX + Tailwind）。
4. 权限“最终裁决”只在服务端与数据库层，不在前端重复实现。

---

## Goals / Non-Goals

### Goals

- 使用单体 FastAPI 架构降低前端状态复杂度与权限漂移风险。
- 统一权限模型：页面权限、API 权限、RLS 权限语义一致。
- 保留双层权限策略：
  - 功能权限：FastAPI 依赖控制
  - 数据权限：PostgreSQL RLS 控制
- 支持列表通用规则：默认 `created_at DESC`，超过 15 条分页，每页 15 条。
- 生产环境不暴露调试端点与敏感配置。

### Non-Goals

- 不引入独立前端服务（React/Vue/Next）。
- 不引入 ORM（SQLAlchemy）作为本变更必需项。
- 不实现 refresh token 自定义机制。
- 不实现密码变更审计日志（沿用 proposal 范围）。

---

## High-Level Architecture

```text
┌───────────────────────────┐
│ Browser                   │
│ - HTML (Jinja2 SSR)       │
│ - HTMX partial updates    │
│ - Tailwind UI             │
└──────────────┬────────────┘
               │ HTTPS
┌──────────────▼────────────┐
│ FastAPI Monolith          │
│ - Web Routes (/login...)  │
│ - API Routes (/api/*)     │
│ - Auth/Role Dependencies  │
│ - Supabase Client Wrapper │
└───────┬─────────┬─────────┘
        │         │
        │         └────────────────────┐
        │                              │
┌───────▼──────────────┐     ┌─────────▼─────────────┐
│ Supabase Auth        │     │ Supabase Storage      │
│ - sign_in/password   │     │ - Word/Excel files    │
│ - forgot/reset       │     │ - signed URL          │
└───────┬──────────────┘     └───────────────────────┘
        │
┌───────▼────────────────────┐
│ Supabase Postgres          │
│ - region / analyst tables  │
│ - RLS policies             │
│ - RPC for atomic actions   │
└────────────────────────────┘
```

---

## Core Decisions

### Decision 1: FastAPI 单体 + SSR 交互模型

**选择：**

- 页面由 FastAPI + Jinja2 渲染。
- 局部交互使用 HTMX（搜索、分页、表单提交、局部刷新）。
- 样式使用 Tailwind，避免大型前端框架状态管理。

**理由：**

- 降低路由守卫、前端 store、组件权限三处重复逻辑。
- 降低“前端状态与后端真实权限不一致”的风险。
- 更适合当前管理后台型需求。

---

### Decision 2: Supabase 仍是唯一数据与认证平台

**选择：**

- 认证：Supabase Auth。
- 数据：Supabase PostgreSQL + RLS。
- 文件：Supabase Storage。
- FastAPI 通过 `supabase-py` / `httpx` 调用平台能力。

**理由：**

- 复用现有基础设施，避免平台迁移成本。
- RLS 权限策略与当前 change 的既定方向一致。

---

### Decision 3: 会话从 localStorage 改为服务端 Cookie

**选择：**

- 登录成功后由 FastAPI 设置 `HttpOnly + Secure + SameSite=Lax` Cookie。
- 每次请求由 FastAPI 从 Cookie 中取 token，并向 Supabase 校验。
- 前端页面不保存 token，不使用 localStorage 持久化认证信息。

**理由：**

- 降低 XSS 下 token 泄漏风险。
- 消除前端 token 状态同步问题。

---

### Decision 4: 权限源头统一

**选择：**

- 页面入口、按钮显示、API 调用都以服务端角色判断为准。
- FastAPI `Depends` 负责功能权限（`require_admin`）。
- Postgres RLS 负责数据权限兜底。

**权限矩阵（本变更）**

| 能力 | Admin | SA | Analyst |
|------|-------|----|---------|
| 登录/登出 | ✅ | ✅ | ✅ |
| 用户管理 | ✅ | ❌ | ❌ |
| Region 管理写操作 | ✅ | ❌ | ❌ |
| Region 数据读取 | ✅ | ✅ | ✅ |
| Analyst 信息写操作 | ✅ | ❌ | ❌ |
| Analyst 数据读取 | ✅ | ✅ | ✅ |
| 管理员直接改密 | ✅ | ❌ | ❌ |

---

### Decision 5: 数据访问不引入 ORM，复杂写操作走 RPC

**选择：**

- 常规 CRUD：Supabase Query API。
- 跨表原子动作：Postgres Function（RPC）由 FastAPI 调用。
- 数据库变更：Supabase SQL migration 管理。

**理由：**

- 在当前 scope 中减少技术层叠。
- 复杂事务留在数据库层更可控。

---

### Decision 6: 列表行为统一落地

**选择：**

- `region`、`analyst` 列表默认 `created_at DESC`。
- `page_size = 15`，总数 > 15 启用分页。
- 搜索与分页同时由后端计算，前端仅渲染结果。

**理由：**

- 与 proposal 通用规则一致。
- 减少页面端二次排序与分页错误。

---

### Decision 7: Region 删除策略遵循 proposal

**选择：**

- 删除 Region 不做“有关联 analyst 即阻断”。
- 由数据库外键 `ON DELETE SET NULL` 自动置空 `analyst.region_id`。

**理由：**

- 与 proposal 中“删除不阻断”一致。
- 简化管理操作与数据修复流程。

---

### Decision 8: 权限拒绝统一返回 403 页面

**选择：**

- 非 Admin 访问管理页面返回 HTTP 403。
- 展示统一 403 页面文案：`无权限`。

**理由：**

- 与 proposal 要求一致。
- 避免“静默重定向到桌面”导致误判。

---

### Decision 9: 调试端点默认禁用

**选择：**

- `/debug/*` 端点仅在开发环境显式开启。
- 生产环境直接不注册调试路由。
- 不返回 service role key 预览等敏感信息。

**理由：**

- 满足提案“生产必须关闭调试端点”的要求。

---

## Data Model & RLS

### Tables

```sql
create table region (
  id uuid primary key default gen_random_uuid(),
  name varchar unique not null,
  code varchar unique not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table analyst (
  id uuid primary key default gen_random_uuid(),
  full_name varchar not null,
  chinese_name varchar,
  email varchar unique not null,
  suffix varchar,
  region_id uuid references region(id) on delete set null,
  sfc varchar,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

### RLS Policies

```sql
alter table region enable row level security;
alter table analyst enable row level security;

create policy "region_select_authenticated"
on region for select to authenticated using (true);

create policy "region_write_admin"
on region for all to authenticated
using ((auth.jwt()->'app_metadata'->>'role') = 'admin')
with check ((auth.jwt()->'app_metadata'->>'role') = 'admin');

create policy "analyst_select_authenticated"
on analyst for select to authenticated using (true);

create policy "analyst_write_admin"
on analyst for all to authenticated
using ((auth.jwt()->'app_metadata'->>'role') = 'admin')
with check ((auth.jwt()->'app_metadata'->>'role') = 'admin');
```

---

## Route Design

### Web Pages（Jinja2）

| Method | Path | 说明 | 权限 |
|-------|------|------|------|
| GET | `/login` | 登录页 | 公开 |
| GET | `/desktop` | 桌面主页 | 已登录 |
| GET | `/users` | 用户管理页 | Admin |
| GET | `/regions` | Region 管理页 | 已登录（写按钮仅 Admin） |
| GET | `/analyst-info` | Analyst 列表页 | 已登录（写按钮仅 Admin） |
| GET | `/403` | 无权限页 | 已登录 |

### API Endpoints

| Method | Path | 说明 | 权限 |
|-------|------|------|------|
| POST | `/api/auth/login` | 登录 | 公开 |
| POST | `/api/auth/logout` | 登出 | 已登录 |
| GET | `/api/auth/me` | 当前用户 | 已登录 |
| POST | `/api/auth/forgot-password` | 发送重置邮件 | 公开 |
| POST | `/api/auth/reset-password` | 重置密码 | 公开（token） |
| GET | `/api/users` | 用户列表（搜索+分页） | Admin |
| POST | `/api/users` | 创建用户 | Admin |
| PUT | `/api/users/{id}` | 更新用户 | Admin |
| PUT | `/api/users/{id}/password` | 管理员改密 | Admin |
| PUT | `/api/users/{id}/role` | 修改角色 | Admin |
| PUT | `/api/users/{id}/toggle-status` | 启用/禁用 | Admin |
| DELETE | `/api/users/{id}` | 删除用户 | Admin |
| GET | `/api/regions` | Region 列表（分页） | 已登录 |
| POST | `/api/regions` | 创建 Region | Admin |
| PUT | `/api/regions/{id}` | 更新 Region | Admin |
| DELETE | `/api/regions/{id}` | 删除 Region | Admin |
| GET | `/api/analyst-info` | Analyst 列表（搜索+分页） | 已登录 |
| POST | `/api/analyst-info` | 创建 Analyst | Admin |
| PUT | `/api/analyst-info/{id}` | 更新 Analyst | Admin |
| DELETE | `/api/analyst-info/{id}` | 删除 Analyst | Admin |
| POST | `/api/analyst-info/check-email` | 邮箱唯一性检查 | Admin |

---

## Interaction Flows

### 登录流程

```text
Browser /login
   -> POST /api/auth/login
      -> Supabase Auth sign_in_with_password
         -> 成功: FastAPI 写入 HttpOnly Cookie
         -> 302 /desktop
```

### 管理写操作流程（以创建 Region 为例）

```text
Browser (Admin)
  -> POST /api/regions
     -> require_admin (FastAPI)
        -> Supabase Postgres insert
           -> RLS admin policy 再次校验
```

### 忘记密码流程

```text
POST /api/auth/forgot-password
  -> Supabase reset password email
  -> 返回统一成功提示（防邮箱枚举）
```

---

## Project Structure（Target）

```text
backend/
  src/
    main.py
    api/
      auth.py
      users.py
      regions.py
      analyst_info.py
    web/
      pages.py
      partials.py
    core/
      config.py
      security.py
      supabase.py
      session.py
    models/
      auth.py
      user.py
      region.py
      analyst.py
    templates/
      base.html
      login.html
      desktop.html
      users/
      regions/
      analyst_info/
      errors/403.html
    static/
      css/
      js/
  migrations/
    *.sql
```

---

## Security & Operations

- Cookie 设置：`HttpOnly`, `Secure`, `SameSite=Lax`, 明确 `Max-Age`。
- 统一异常输出，避免泄露内部堆栈与密钥。
- 生产环境不注册 debug router。
- 所有管理员写操作记录操作人 ID 与时间（如 `updated_by` 字段可在后续扩展）。

---

## Risks / Trade-offs

| 风险 | 影响 | 缓解 |
|------|------|------|
| 过度依赖 Supabase API | 平台耦合 | 关键事务放 RPC，接口层封装网关 |
| SSR 页面可交互上限低于 SPA | 复杂前端体验受限 | 本变更聚焦管理后台，优先稳定性 |
| Cookie 会话需要 CSRF 防护 | 安全风险 | 对写操作引入 CSRF token 校验 |
| 现有 artifact 与旧前端栈有差异 | 文档不一致 | 后续同步 proposal/specs/tasks |

---

## Alignment Notes（本次重构影响）

本设计已明确替换此前的 `Vue + Axios + localStorage + Router Guard` 方案。  
为避免 artifact 漂移，后续应按本设计同步更新：

1. `specs/login-page/spec.md`（去除 Vue/localStorage 表述）
2. `specs/desktop-page/spec.md`（去除前端路由守卫语义，改服务端鉴权）
3. `specs/user-auth/spec.md`（会话存储改为 HttpOnly Cookie）
4. `tasks.md`（替换前端实现任务为模板+HTMX任务）

