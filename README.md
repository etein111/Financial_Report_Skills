# Neolyst

## 技术栈

- FastAPI (SSR + API)
- Jinja2 + HTMX + Tailwind
- Supabase (Auth + Postgres + RLS)

## 快速开始

### 1) 后端

```bash
cd backend
# 开发阶段真实配置已提交到仓库：backend/.env
uv sync
uv run uvicorn src.main:app --reload --port 8000
```

### 2) Supabase 数据库迁移

```bash
supabase db push
```

Seed 文件配置在 `supabase/config.toml` 中：

- `supabase/seed/regions.sql`

迁移完成后，会通过迁移初始化一个默认管理员账户：

- `admin@neolyst.com / Admin123`

## 发布流程

1. 将迁移推送到 `dev` 环境。
2. 在 `dev` 环境验证 API/页面行为和 RLS 策略。
3. 将迁移推送到 `prod` 环境。

详细规则请参考：`docs/migration-release-rules.md`。
