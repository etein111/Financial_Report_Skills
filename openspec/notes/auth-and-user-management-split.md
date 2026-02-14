# Auth & User Management 拆分备忘（OpenSpec）

最后更新：2026-02-14

## 目的

你可能会退出 Codex 重新进入；本备忘用于把关键决策与下一步工作方式固化到仓库里，便于我在新会话里通过读取本文件快速恢复上下文并继续执行。

## 已确认的关键决策（不再回溯历史）

- 技术栈：Next.js（App Router）+ Supabase 原生能力（Auth/Postgres/RLS/PostgREST）。
- 会话：按 Supabase SSR 推荐做法走 cookies；不额外强制 HttpOnly（避免破坏 refresh 链路）。
- 交互：Server-first（Server Components + Server Actions）；仅必要场景使用 Route Handlers（例如 auth callback）。
- 不使用：Supabase Edge Functions（原则：简单优先）。
- 登录方式：仅邮箱+密码（不引入 OAuth providers）。
- 用户创建：邀请制（public signups 必须关闭）。
- 账号启用/禁用：只用一个机制 ban/unban（不使用 `app_metadata.is_active` 作为账号状态事实源）。
- 角色事实源：`app_metadata.role`。
- Desktop 导航契约：Desktop 作为 launcher；功能卡片点击在新标签页打开；功能页不提供“返回桌面”链接。
- 默认 Admin 引导账号（Dev/引导用，生产必须改密/替换）：
  - email：`jiang_jiahong@qq.com`
  - password：`Admin123`

## 拆分方案（已确认）

我们不在现有大 change（`openspec/changes/auth-and-user-management`）上继续改动，把它当作“参考与清单”冻结。

新建 3 个 change（只先拆 `proposal.md` + `design.md`，暂不生成/调整 `tasks.md` 与 `specs/*`）：

1. `openspec/changes/ui-prototype-core-pages`
   - 目标：界面原型，用于确认视觉风格、导航方式、界面元素样式与交互方式。
   - 范围：只做 Login、Desktop、Users（用户管理）三页的原型（可用 mock 数据）。

2. `openspec/changes/auth-and-users-mvp`
   - 目标：搭系统框架，把登录相关、Desktop、Users 管理跑通（可用本地 Supabase）。
   - 范围：Supabase SSR cookies、middleware 路由保护、invite/role/ban/admin 改密等闭环。
   - 不包含：Regions/Analyst Info 功能页与 CRUD。

3. `openspec/changes/region-and-analyst-management`
   - 目标：实现 Regions + Analyst Info 管理功能与权限控制。
   - 范围：CRUD + Admin-only 页面入口与操作约束；RLS 作为数据层兜底。

工作方式：
- 我先生成每个 change 的 `proposal.md` / `design.md` 初稿。
- 你逐个审阅、补充、讨论确认后，我再为该 change 重新生成对应的 `tasks.md` 与 `specs/*`（以最终 proposal/design 为准）。
- 三个 change 逐个完成，不并行推进实现。

## 参考资料（冻结的大 change）

- 大 change（冻结）：`openspec/changes/auth-and-user-management`
- 参考图片：
  - `openspec/changes/ui-prototype-core-pages/01-login-page.jpg`
  - `openspec/changes/ui-prototype-core-pages/02-desktop.jpg`

## 关键实现文件（当前仓库事实）

- Supabase migrations（已存在）：
  - `supabase/migrations/20260213165658_init_default_admin.sql`（默认 Admin：`jiang_jiahong@qq.com` / `Admin123`，角色来源 `app_metadata.role`）
  - `supabase/migrations/20260214094418_auth_and_user_management_baseline.sql`（region/analyst 表与 RLS）
- Supabase 本地配置：
  - `supabase/config.toml`（`auth.site_url=http://localhost:3000`，redirect urls 包含 `http://localhost:3000/**`）

## 已知环境提示

- 本机 `git` 可能因 “dubious ownership / safe.directory” 报错；如需用 git 命令，需要先配置 safe.directory（后续再处理）。

## 新会话如何继续

1. 让 Codex 先读取：`openspec/notes/auth-and-user-management-split.md`
2. 再从 3 个新 change 的 `proposal.md` / `design.md` 开始逐个 review 与收敛。
