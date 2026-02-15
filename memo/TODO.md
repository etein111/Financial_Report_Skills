# TODO (Codex Handoff) - 2026-02-15

本文用于明天重启 Codex 后快速恢复上下文，继续解决 Supabase 云端阻塞并完成 OpenSpec change：`auth-and-users-mvp`。

## 0. 当前结论（最重要）

- Supabase 云项目 `lvakvjjnyvcrwacjwjcn` 当前 **Auth API 500**：
  - `auth.admin.listUsers(...)` 返回 `AuthApiError 500: Database error finding users`
  - `signInWithPassword(...)` 返回 `AuthApiError 500: Database error querying schema`
- 但 PostgREST/数据库本体是 OK 的：
  - 直连 Postgres 已确认 `auth` schema 与 `auth.users/auth.identities` 存在，默认 Admin 行存在
  - `public.region` 查询正常
  - 默认 Admin migration 幂等且不改密码 + RLS 验收已通过（见脚本）
- 用于管理 API 的 PAT（`supabase/supabase_access.token`）目前 **401 Unauthorized**，导致无法通过 API/CLI 执行 pause/restore 等操作。

下一步的关键阻塞是：
1. 拿到一个有效的 Supabase PAT（Personal Access Token）写入 `supabase/supabase_access.token`
2. 用该 PAT 对项目做一次 pause+restore（软重启），再复测 Auth 500 是否恢复

## 1. 目录与密钥文件（已调整）

- token 文件已从根目录移动到 `supabase/`：
  - `supabase/supabase_access.token`：Supabase PAT（只用于 CLI/管理 API）
  - `supabase/supabase_db_password.token`：远端 Postgres `postgres` 用户密码（用于 `supabase db push -p`）
- `supabase/README.md` 已重写：说明目录作用、标准、CLI 经验、版本管理流程、踩坑点（例如 `db push` 不支持 `--project-ref`）。

安全备注：
- 聊天里曾出现过 token/password（历史原因）。建议在 Supabase 侧 revoke/rotate（不要再发到聊天里）。

## 2. OpenSpec 状态

- Change：`openspec/changes/auth-and-users-mvp`
- Schema：`spec-driven`
- 最新进度：`53/58`，剩余 `5` 项：
  - 7.1 认证闭环验收（登录/登出/会话刷新/忘记密码/回调）
  - 7.2 权限验收（Admin/SA/Analyst）
  - 7.3 禁用账号验收（ban 后无法登录/访问）
  - 7.4 路由保护验收（未登录访问 /desktop /users -> /login）
  - DoD：`/opsx:verify`

已补齐并勾选：阶段 1.1-1.4、2.1-2.4、6.2-6.9（其中 1.4/2.4 用 DB 直连脚本验收通过）。

## 3. Supabase 配置与迁移（当前事实）

- `supabase/config.toml`
  - `project_id = "lvakvjjnyvcrwacjwjcn"`
  - `[auth] site_url = "http://localhost:3000"`
  - `additional_redirect_urls = ["http://localhost:3000/**"]`
  - `enable_signup = false`
  - seed：`supabase/seed/regions.sql`
- migrations（云端已 `db push` 成功；`supabase migration list --linked` 可见 Local/Remote 对齐）：
  - `supabase/migrations/20260215122000_region_analyst_rls_baseline.sql`
  - `supabase/migrations/20260215122100_init_default_admin.sql`

## 4. Web 侧实现关键点（当前事实）

- `/users` 已从原型 mock 升级为真实 Admin API（服务端 service role）：
  - `web/features/users/repo/users-admin-repo.ts`
  - `web/features/users/actions.ts`
  - `web/features/users/components/users-page.tsx`（Server，读取 search params）
  - `web/features/users/components/users-page-client.tsx`（Client，调用 server actions）
  - created 时间展示按 `Asia/Shanghai`：`web/lib/time.ts`
- `/desktop` 顶栏增加 welcome：`web/app/desktop/page.tsx`
- `/auth/callback` 的 OTP type 改为本地 union（去掉 `@supabase/auth-js` 依赖）：`web/app/auth/callback/route.ts`
- `web/.env` 已切换到新项目 URL/keys（注意：不要把 service role key 下发到浏览器，代码里已 `server-only` 限制 admin client）

## 5. 诊断/验收脚本（无需 Docker/psql）

1) DB 直连验收：默认 Admin 幂等不改密码 + RLS（已跑通）
- `web/scripts/verify/verify-db-admin-and-rls.mjs`
- 运行：
```powershell
cd web
node scripts/verify/verify-db-admin-and-rls.mjs
```

2) DB 直连诊断 Auth（用于确认 `auth.*` 基础表与默认 Admin）
- `web/scripts/verify/diagnose-auth-500.mjs`

说明：
- 两个脚本都读取 `supabase/supabase_db_password.token` 来直连 `db.<ref>.supabase.co:5432`。

## 6. 需要继续解决的云端阻塞（明天优先做）

### 6.1 让 PAT 生效（解决 401）

现状：
- 从 `supabase/supabase_access.token` 读 token 后：
  - `supabase projects list` -> 401
  - `supabase/scripts/pause-restore.ps1` -> 401

明天动作：
1. 在 Supabase 个人设置重新生成一个新的 PAT
2. 把“纯 token 字符串”写入 `supabase/supabase_access.token`
   - 不要带 `SUPABASE_ACCESS_TOKEN=`
   - 不要引号
   - 不要空格/换行（末尾换行没关系）
3. 验证：
```powershell
$env:SUPABASE_ACCESS_TOKEN = (Get-Content -Raw supabase/supabase_access.token).Trim()
supabase projects list --output json
```

### 6.2 对项目 pause + restore（软重启）

- 脚本：`supabase/scripts/pause-restore.ps1`
- 运行（依赖上一步 PAT 生效）：
```powershell
.\supabase\scripts\pause-restore.ps1 -ProjectRef lvakvjjnyvcrwacjwjcn
```

如果脚本跑通，会打印状态从 ACTIVE -> INACTIVE -> ACTIVE。

### 6.3 复测 Auth API 是否恢复

用 service role 调 Admin API（成功则 Auth 恢复）：
```powershell
cd web
node --input-type=module -e "import fs from 'node:fs'; import { createClient } from '@supabase/supabase-js'; const raw=fs.readFileSync('.env','utf8'); for (const line of raw.split(/\r?\n/)) { const t=line.trim(); if(!t||t.startsWith('#')) continue; const i=t.indexOf('='); if(i<0) continue; const k=t.slice(0,i).trim(); const v=t.slice(i+1).trim(); if(!(k in process.env)) process.env[k]=v; } const url=process.env.NEXT_PUBLIC_SUPABASE_URL; const key=process.env.SUPABASE_SERVICE_ROLE_KEY; const supabase=createClient(url,key,{auth:{autoRefreshToken:false,persistSession:false}}); const {data,error}=await supabase.auth.admin.listUsers({page:1,perPage:1}); console.log({ok:!error, err:error?.message});"
```

以及用 anon key 做一次登录验证（成功则登录闭环可跑）：
```powershell
cd web
node --input-type=module -e "import fs from 'node:fs'; import { createClient } from '@supabase/supabase-js'; const raw=fs.readFileSync('.env','utf8'); for (const line of raw.split(/\\r?\\n/)) { const t=line.trim(); if(!t||t.startsWith('#')) continue; const i=t.indexOf('='); if(i<0) continue; const k=t.slice(0,i).trim(); const v=t.slice(i+1).trim(); if(!(k in process.env)) process.env[k]=v; } const url=process.env.NEXT_PUBLIC_SUPABASE_URL; const anon=process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY; const email=process.env.TEST_LOGIN_EMAIL; const password=process.env.TEST_LOGIN_PASSWORD; if(!email||!password){ console.error('Missing TEST_LOGIN_EMAIL/TEST_LOGIN_PASSWORD (do not commit).'); process.exit(2);} const supabase=createClient(url,anon,{auth:{autoRefreshToken:false,persistSession:false}}); const {data,error}=await supabase.auth.signInWithPassword({email,password}); console.log({ok:!error, err:error?.message, hasSession:!!data.session});"
```

如果仍然 500：
- 优先方案：在 Dashboard 手动重启/restore 项目（或新建 project）。
- 备选方案：继续用 DB 直连脚本检查 `auth.schema_migrations` 等，但通常是平台侧 gotrue 连接异常。

## 7. 联调验收（完成 tasks 7.1-7.4）

前提：Auth 500 已恢复。

1) 启动 Web（注意端口/锁）
- 之前出现过 `next dev` 锁冲突：`.next/dev/lock`
- 之前 3000 被某个 node 占用（PID 31052），现在已释放

建议启动：
```powershell
cd web
corepack pnpm dev
```

2) 依次验收：
- 未登录访问 `/desktop`、`/users` -> 跳 `/login`
- Admin 登录 -> `/desktop` 可见 Users 卡片；打开 `/users` 正常
- 邀请用户后，完成邀请回调应进入 `/desktop`
- SA/Analyst 登录 -> `/desktop` 不显示 Users 卡；直接访问 `/users` -> `/403`（含 `No permission`）
- Ban 用户后：该用户无法继续登录/访问受保护路由

完成后把 `openspec/changes/auth-and-users-mvp/tasks.md` 的 7.1-7.4 + DoD 勾掉，并执行：
```powershell
openspec verify --change auth-and-users-mvp
```

## 8. 其它工程注意事项

- `git status` 可能触发 “dubious ownership / safe.directory” 报错；可临时用：
  - `git -c safe.directory=C:/_code/neolyst status --short`
- 用户要求保留 `AGENTS.md` 与 `CLAUDE.md` 的现有改动，不要回退。

## 9. 规范文件位置（已迁移）

Web 侧强约定已迁移到 `docs/` 根目录：
- `docs/LOGIC.md`
- `docs/UI.md`

会话备忘机制：
- 行动清单：`memo/TODO.md`
- 长篇备忘：`memo/`（见 `memo/README.md`）
- OpenSpec 相关上下文：同样放 `memo/`（按文件名区分场景）

## 10. OpenSpec 归档改进方案（待实施）

**问题**：归档时没有生成系统级的需求和设计汇总文档。

**方案**：
1. 在 `openspec/` 下新增 `REQUIREMENTS.md` 和 `ARCHITECTURE.md`
2. 扩展 `openspec/config.yaml`：
   ```yaml
   schema: spec-driven
   system_docs:
     requirements: REQUIREMENTS.md
     architecture: ARCHITECTURE.md
   ```
3. 修改 `openspec-archive-change` skill，归档时更新系统文档

**触发机制**：所有 openspec skills 都会读取 `config.yaml`，archive skill 额外读取 `system_docs` 字段来更新。

**待确定**：
- 更新粒度（追加 vs 重写）
- 冲突处理
- 回滚机制

**关联**：
- `.claude/skills/openspec-archive-change/SKILL.md`
- `.claude/skills/openspec-bulk-archive-change/SKILL.md`
