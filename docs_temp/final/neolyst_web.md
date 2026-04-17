# Neolyst-Web 技术栈

## 业务需求(todo)

## 技术栈

- 前端：Next.js App Router + React + TypeScript。
- 后端能力：Supabase（Auth / Postgres / RLS / PostgREST / Storage）。
- 当前不使用：Edge Functions、Realtime（除非后续 change 明确引入）。

## 架构概览

```text
Browser
  -> Next.js (App Router)
      - Server Components / Server Actions / Route Handlers
      - Request boundary gate: proxy.ts（会话刷新 + 轻量门禁）
      -> Supabase
```

## 分层架构

- Next.js 是唯一应用入口。
- 路由与页面组合：`web/app`
- 业务模块：`web/features`
- 业务领域类型与纯规则：`web/domain`
- 基础 UI：`web/components`
- 基础设施：`web/lib`

## 认证与授权

- 应用层权限控制 + RLS 双层防护。
- Supabase 承担认证、数据访问与数据权限兜底。
- 会话载体：SSR cookies（`@supabase/ssr`）。
- 服务端鉴权事实源：`getUser()`。
- 路由门禁：`proxy.ts` 做"未登录拦截 + 轻量权限拦截"。
- 资源级权限：通过应用层权限 + RLS 共同实现。
