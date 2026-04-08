# Supabase 多环境管理方案

三个环境，各自独立：

- **本地 Docker** — 开发调试，数据随时可重建
- **Staging（supabase.com）** — 给业务人员演示和测试
- **Production（supabase.com）** — 正式上线（未来启用）

**一条铁律：所有数据库变更只在本地做，通过迁移文件同步到远程。不要在远程 Dashboard 上直接改 schema。**

---

## 场景一：第一次搭建本地环境

> **Windows 用户注意：** 不要装 Docker Desktop。Docker Desktop 通过 Windows 网络栈拉取镜像，部分 Supabase 镜像托管在美国，容易拉取失败。直接在 WSL 里装 Docker Engine：
>
> ```bash
> # 在 WSL (Ubuntu) 中执行
> curl -fsSL https://get.docker.com | sh
> sudo usermod -aG docker $USER
> # 重新登录 WSL 使 docker 组生效
> ```
>
> WSL 内的 Docker 走 Linux 网络栈，可以通过配置代理等方式自由控制网络，不存在 Docker Desktop 的镜像拉取问题。

```bash
npm install supabase --save-dev
npx supabase init
npx supabase start          # 首次启动拉取 Docker 镜像，需几分钟
```

启动后输出本地服务地址，记住这几个：

```text
API URL:       http://localhost:54321
Studio UI:     http://localhost:54323     ← 可视化管理数据库
DB:            postgresql://postgres:postgres@localhost:54322/postgres
```

如果 Staging 上已有数据库 schema，先拉下来：

```bash
npx supabase login
npx supabase link --project-ref <STAGING_PROJECT_ID>
npx supabase db pull
```

## 场景二：改了数据库 schema

在 Studio UI（`http://localhost:54323`）里操作 Table Editor，然后导出为迁移文件并提交：

```bash
npx supabase db diff -f add_employees     # 导出迁移文件
# 检查 supabase/migrations/ 下生成的 SQL，确认无误后提交
git add supabase/migrations/ && git commit
npx supabase db reset                     # 重建本地库验证
```

迁移文件是唯一事实源，提交到 Git，跨环境全靠它同步。目录结构：

```text
supabase/
├── config.toml       # 本地配置，不影响远程
├── seed.sql          # 测试/演示数据
└── migrations/       # 迁移文件（提交到 Git）
```

## 场景三：推到 Staging 给业务演示

```bash
npx supabase link --project-ref <STAGING_PROJECT_ID>   # 关联目标项目
npx supabase db push                                   # 推送未应用的迁移
```

project-ref 在 Supabase Dashboard → Settings → General 里找。首次 link 需输入数据库密码，之后保存在本地 `.supabase/`（已在 .gitignore 中）。

Production 流程完全一样，换 project-ref 即可。

前端环境变量（`NEXT_PUBLIC_SUPABASE_URL`、`NEXT_PUBLIC_SUPABASE_ANON_KEY`）根据部署环境切换，本地用 `.env.local`，远程用部署平台的环境变量。

## 场景四：准备测试和演示数据

`supabase/seed.sql` 在 `db reset` 时自动执行。只写数据操作，不写建表语句：

```sql
INSERT INTO analysts (id, name, email, role) VALUES
  ('a001', '张三', 'zhangsan@example.com', 'analyst')
ON CONFLICT DO NOTHING;
```

用 `ON CONFLICT DO NOTHING` 保证幂等，这样 Staging 也能安全执行：

```bash
npx supabase link --project-ref <STAGING_PROJECT_ID>
npx supabase db seed
```

---

## 官方文档

- [Managing Environments](https://supabase.com/docs/guides/deployment/managing-environments) — 多环境完整方案、CI/CD、GitHub Actions 示例
- [Local Development](https://supabase.com/docs/guides/local-development) — 本地环境搭建、CLI 使用、Studio 操作
- [Seeding Your Database](https://supabase.com/docs/guides/local-development/seeding-your-database) — 种子数据配置
- [CLI Reference](https://supabase.com/docs/guides/cli) — 全部命令参考
- [Database Migrations](https://supabase.com/docs/guides/database/migrations) — 迁移机制原理、冲突处理
- [Production Readiness](https://supabase.com/docs/guides/deployment/production-readiness) — 上线前检查清单
