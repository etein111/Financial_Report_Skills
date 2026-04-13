# Supabase 开发规范

## 环境

| 环境 | 运行方式 | 用途 |
|------|----------|------|
| local | 本地 Docker（`supabase start`） | 开发与测试 |
| staging | Zeabur 上的 PostgreSQL（裸机） | 演示与集成测试 |
| production | 暂未部署 | — |

## 目录结构

```text
supabase/
├── config.toml              # 本地 Supabase 服务配置
├── seed.sql                 # 种子数据（db reset 时自动加载）
├── staging.json             # Zeabur staging DB 连接信息
├── migrations/              # Schema 迁移文件（唯一事实源）
├── snippets/                # SQL 片段（手工执行，不自动加载）
├── tests/
│   └── test_data.sql        # 测试数据（手工导入）
└── SUPABASE_STANDARDS.md    # 本文件
```

## 本地开发

### 依赖

- Docker（WSL 内安装 Docker Engine，不要用 Docker Desktop）
- Supabase CLI

### 常用命令

```bash
supabase start                        # 启动本地环境
supabase db reset                     # 重建数据库（重放全部 migration + seed.sql）
supabase migration new <描述>          # 创建新迁移文件（自动生成时间戳）
```

### 创建迁移文件

**必须用 `supabase migration new`**，让 CLI 自动生成时间戳。不要手动创建迁移文件。

```bash
supabase migration new add_user_table
# 生成: supabase/migrations/20260413140000_add_user_table.sql
```

迁移文件规则（详见 [principles/ARCHITECTURE.md](../principles/ARCHITECTURE.md)）：

- 只追加，不修改已提交的迁移文件
- `create or replace` 覆盖函数时以数据库当前版本为准，不从旧迁移复制文本

### 导入测试数据

```bash
psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres" \
     -f supabase/tests/test_data.sql
```

## Staging 部署

Staging 是 Zeabur 上的 PostgreSQL 实例，通过自定义脚本推送迁移。

### 推送命令

```bash
python3 supabase/push_zeabur_com.py
```

### 工作原理

1. 从 `supabase/staging.json` 读取连接信息
2. 直连远端 PostgreSQL（`psql`），不经过 Supabase CLI
3. 按 `supabase/migrations/*.sql` 文件名排序逐个应用
4. 跳过已应用的迁移（通过 `supabase_migrations.schema_migrations` 表追踪）

### staging.json 格式

```json
{
  "host": "IP 地址",
  "port": "端口号",
  "user": "supabase_admin",
  "password": "密码",
  "dbname": "postgres"
}
```

## Production 部署

暂未部署。待生产环境确定后，建议通过 `supabase link` + `supabase db push` 管理，不复用 staging 推送脚本。

## 参考文档

- [Supabase Local Development](https://supabase.com/docs/guides/local-development)
- [Database Migrations](https://supabase.com/docs/guides/database/migrations)
- [Managing Environments](https://supabase.com/docs/guides/deployment/managing-environments)
- [CLI Reference](https://supabase.com/docs/guides/cli)
