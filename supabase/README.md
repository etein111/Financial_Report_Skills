# supabase/

Schema 迁移、种子数据、staging 部署。

## 目录结构

```
supabase/
├── config.toml                # 本地 Supabase 服务配置（端口、SMTP 等）
├── staging.json               # Zeabur staging DB 连接信息
├── seed.sql                   # 种子数据（db reset 时自动加载）
├── push_zeabur_com.py         # Staging 迁移推送脚本
├── migrations/                # Schema 迁移文件（唯一事实源）
└── tests/
    └── test_data.sql          # 测试数据（手工导入，不随 reset 加载）
```

## 环境

| 环境 | 运行方式 | 用途 |
|------|----------|------|
| local | 本地 Docker（`supabase start`） | 开发与测试 |
| staging | Zeabur 上的 PostgreSQL（裸机） | 演示与集成测试 |
| production | 暂未部署 | — |

## Staging 部署

```bash
python3 supabase/push_zeabur_com.py
```
直连远端 PostgreSQL（`psql`），按文件名排序逐个应用 `migrations/*.sql`，已应用的自动跳过。连接信息从 `staging.json` 读取。

## 常用操作

```bash
supabase start                                          # 启动本地环境
supabase db reset                                       # 重建数据库（migrations + seed.sql）
supabase migration new <描述>                            # 创建新迁移文件
psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres" -f supabase/tests/test_data.sql  # 导入测试数据
python3 supabase/push_zeabur_com.py                     # 推送到 staging
```
