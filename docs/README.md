# Docs

这是一组“跨目录、长期有效”的项目规范与约定。面向人和 AI 工具共同阅读。

约定：
- `docs/README.md` 是唯一入口与索引。
- `docs/` 下除 `README.md` 外的文件：彼此不相互引用；每个文件只负责一类事情。

建议阅读顺序：
1. `docs/DECISIONS.md`：跨后续功能的关键约束/约定（从 design/proposal 收敛而来）
2. `docs/TESTING.md`：测试与验收规范（尤其是临时文件目录 `temp/`）
3. `docs/LOGIC.md`：Web 逻辑与分层硬约定（优先级最高）
4. `docs/UI.md`：Web UI 组件规范

子系统文档：
- Web（Next.js）：`docs/LOGIC.md`、`docs/UI.md`（强约定；冲突以 `docs/LOGIC.md` 为准）
- Supabase：`supabase/README.md`
- 变更（OpenSpec）：`openspec/`

## Web (Next.js)

Next.js 应用，系统前端界面。

### 技术栈

- Next.js 16 (App Router)
- React 19
- Tailwind CSS 4
- TypeScript 5
- Supabase (Auth + Postgres + RLS)

### 开发

```bash
# 安装依赖
pnpm install

# 启动开发服务器
pnpm dev

# 构建
pnpm build

# 生产运行
pnpm start

# 代码检查
pnpm lint
```

### 目录结构

```text
web/
├─ app/             # Next.js App Router
├─ components/      # React 组件
├─ lib/             # 工具库
├─ public/          # 静态资源
└─ .env             # 环境变量
```

### Web 规范文档

- UI 组件与交互规范：`docs/UI.md`
- 逻辑处理规范（鉴权/RBAC/错误处理/时间等）：`docs/LOGIC.md`

### 环境变量

在 `web/.env` 中配置：

```bash
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
```

### Web 代码问题清单

短期问题清单与排障记录属于“会话备忘”，统一放在 `memo/`（不要放在 `docs/`）。
