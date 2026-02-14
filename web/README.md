# Neolyst Web

Next.js 应用，系统前端界面。

## 技术栈

- Next.js 16 (App Router)
- React 19
- Tailwind CSS 4
- TypeScript 5
- Supabase (Auth + Postgres + RLS)

## 开发

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

## 目录结构

```
web/
├─ app/             # Next.js App Router
├─ components/      # React 组件
├─ lib/             # 工具库
├─ public/          # 静态资源
└─ .env             # 环境变量
```

## 规范文档

- UI 组件与交互规范：`COMPONENTS.md`
- 逻辑处理规范（鉴权/RBAC/错误处理/时间等）：`LOGIC.md`

## 环境变量

在 `.env` 中配置：

```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
```
