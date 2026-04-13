# Supabase 规范

## 根本原则

`supabase/` 目录是数据库 schema 的唯一事实源。所有环境（本地、staging、production）的数据库结构必须与此保持一致，不允许任何环境脱离 migrations 独立修改 schema。

## 目录结构

`supabase/` 必须包含：

- `config.toml` — 本地服务配置
- `seed.sql` — 种子数据（db reset 时自动加载）
- `migrations/` — Schema 迁移文件

## 环境

- 所有数据库结构变更只在本地完成。
- 开发必须用 Supabase CLI，不手动操作数据库。
- Windows 系统必须在 WSL 内安装 Docker Engine，不要用 Docker Desktop。

## 迁移文件

- 所有 schema 变更（表、函数、触发器、RPC）必须写入 `supabase/migrations/` 文件。
- 迁移文件必须用 `supabase migration new <name>` 创建，不手动拼时间戳。
- 迁移文件只追加，不修改；已提交的迁移文件不可编辑，所有变更通过新建迁移文件实现。
- `create or replace` 覆盖函数时以数据库当前版本为准，不从旧迁移复制文本。
- 远端环境只通过 migration 同步，不直接在 Dashboard 改 schema。

## 参考文档

- [Supabase Local Development](https://supabase.com/docs/guides/local-development)
- [Database Migrations](https://supabase.com/docs/guides/database/migrations)
- [Managing Environments](https://supabase.com/docs/guides/deployment/managing-environments)
- [CLI Reference](https://supabase.com/docs/guides/cli)
