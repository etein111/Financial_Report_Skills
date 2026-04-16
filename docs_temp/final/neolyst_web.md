# web技术栈

本文件定义系统架构与技术边界（HOW-系统级）。
待补充：
依赖方向、触库规则、Server Actions 约束见 `docs/LOGIC.md`。

## 2. 技术栈

- 前端：Next.js App Router + React + TypeScript。
- 后端能力：Supabase（Auth / Postgres / RLS / PostgREST / Storage）。
- 当前不使用：Edge Functions、Realtime（除非后续 change 明确引入）。

## (标题待定)

```text
Browser
  -> Next.js (App Router)
      - Server Components / Server Actions / Route Handlers
      - Request boundary gate: proxy.ts（会话刷新 + 轻量门禁）
      -> Supabase
```

## 3. 分层架构（系统层）

- Next.js 是唯一应用入口。
- 路由与页面组合：`web/app`
- 业务模块：`web/features`
- 业务领域类型与纯规则：`web/domain`
- 基础 UI：`web/components`
- 基础设施：`web/lib`

## 权限控制

- 应用层权限控制 + RLS 双层防护。
- Supabase 承担认证、数据访问与数据权限兜底。

## 4. 认证与授权架构

- 会话载体：SSR cookies（`@supabase/ssr`）。
- 服务端鉴权事实源：`getUser()`。
- 角色事实源遵循 `docs/DECISIONS.md` 的 `D-003`。
- 路由门禁：`proxy.ts` 做“未登录拦截 + 轻量权限拦截”。
- 资源级权限：通过应用层权限 + RLS 共同实现。
