# Supabase 目录与部署约定

## 1. 环境和目录结构约定

本项目固定使用三套环境：

- `local`：本地 Docker 开发环境
- `staging`：测试/演示环境
- `production`：正式环境

统一原则：

- 所有数据库结构变更只在本地完成
- 所有 schema 变更必须进入 `supabase/migrations/`
- 远端环境只通过 migration 同步，不直接在 Dashboard 改 schema
- 当前 Supabase 本地项目名固定为 `project_id = "neolyst"`

仓库内的标准目录：

```text
supabase/
├── config.toml
├── migrations/
├── seed.sql
├── tests/
│   └── test_data.sql
├── push_staging.py
└── SUPABASE_STANDARDS.md
```

目录用途：

- `migrations/`：数据库结构的唯一事实源
- `seed.sql`：默认初始化数据入口，随 `supabase db reset` 和 `db push --include-seed` 执行
- `tests/test_data.sql`：测试数据，不默认自动执行
- `push_staging.py`：测试环境一键推送脚本

## 2. 安装本地开发环境

Windows 用户注意：

- 不要使用 Docker Desktop 作为 Supabase 本地开发环境
- Docker Desktop 走 Windows 网络栈，代理和翻墙链路更复杂，很多翻墙软件对它不起作用
- Supabase 依赖的部分镜像托管在美国，使用 Docker Desktop 拉取时经常失败
- 更稳的做法是在 WSL 中安装 Docker Engine，并在 WSL 内运行 `supabase start`

本地开发依赖：

- Docker
- Supabase CLI

初始化和启动：

```bash
supabase start
```

常用命令：

```bash
supabase db reset
supabase db diff -f <migration_name>
```

说明：

- `supabase start` 用于启动本地开发环境
- `supabase db reset` 用于重建本地数据库并验证 migration 可完整回放
- `supabase db diff -f <migration_name>` 用于从本地改动生成新的 migration

本地开发的推荐流程：

1. 在本地调整数据库结构
2. 生成 migration
3. 人工检查 SQL
4. 执行 `supabase db reset`
5. 提交代码

## 3. 部署 Staging 环境

推荐流程：

```bash
supabase link --project-ref <STAGING_PROJECT_REF>
supabase migration list --linked
supabase db push --include-seed
```

说明：

- 先执行 `migration list --linked`，确认远端没有漂移
- 再执行 `db push --include-seed`，同步 migration 和默认初始化数据

如果当前测试环境沿用仓库内置脚本，也可以直接运行：

```bash
python supabase/push_staging.py
```

这个脚本只适用于当前测试环境，不适用于 production。

## 4. 部署 Production 环境

Production 的流程与 staging 相同，但必须使用 production 自己的项目配置和凭证。

推荐流程：

```bash
supabase link --project-ref <PRODUCTION_PROJECT_REF>
supabase migration list --linked
supabase db push --include-seed
```

要求：

- 不复用 staging 的 `project-ref`
- 不复用 staging 的访问令牌和数据库密码
- 推送前先确认本地 migration 与远端状态一致

如需生产环境自动化，建议单独维护 production 专用脚本或 CI 流程，不直接复用测试脚本。

## 5. 参考文档

- [Managing Environments](https://supabase.com/docs/guides/deployment/managing-environments)
- [Local Development](https://supabase.com/docs/guides/local-development)
- [Seeding Your Database](https://supabase.com/docs/guides/local-development/seeding-your-database)
- [CLI Reference](https://supabase.com/docs/guides/cli)
- [Database Migrations](https://supabase.com/docs/guides/database/migrations)
- [Production Readiness](https://supabase.com/docs/guides/deployment/production-readiness)
