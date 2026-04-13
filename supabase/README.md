# supabase/

Supabase 相关文件：schema 迁移、种子数据、staging 环境配置。

## 目录结构

```
supabase/
├── config.toml                # Supabase 本地服务配置（端口、SMTP 等）
├── staging.json               # Zeabur staging 环境 DB 连接信息
├── seed.sql                   # 基础种子数据（db reset 时自动加载）
├── SUPABASE_STANDARDS.md      # Supabase 开发规范
├── migrations/                # Schema 迁移文件，按文件名编号顺序执行
└── tests/
    └── test_data.sql          # 测试数据（手工导入，不随 reset 加载）
```

## 主要文件说明

| 文件 | 用途 |
|------|------|
| `config.toml` | 本地 Supabase 服务配置，`supabase start` 时读取 |
| `staging.json` | Zeabur 远端 DB 连接信息（host/port/user/password），供 `push_zeabur_com.py` 使用 |
| `seed.sql` | 管理员账号、字典表（rating/region/sector/report_type）、模板占位记录等初始数据 |
| `SUPABASE_STANDARDS.md` | SQL 编写、迁移命名、RLS 等开发规范 |

## 常用操作

```bash
# 启动本地 Supabase
supabase start

# 重置本地数据库（执行 migrations + seed.sql）
supabase db reset

# 导入测试数据
psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres" -f supabase/tests/test_data.sql

# 推送 schema 到 staging
python3 supabase/push_zeabur_com.py
```
