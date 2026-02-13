# Neolyst

## Stack

- FastAPI (SSR + API)
- Jinja2 + HTMX + Tailwind
- Supabase (Auth + Postgres + RLS)

## Quick Start

### 1) Backend

```bash
cd backend
# 开发阶段真实配置已提交到仓库：backend/.env
uv sync
uv run uvicorn src.main:app --reload --port 8000
```

### 2) Supabase Migration

```bash
supabase db push
```

Seed file is configured in `supabase/config.toml`:

- `supabase/seed/regions.sql`

After migration, a default admin account is initialized by migration:

- `admin@neolyst.com / Admin123`

## Release Order

1. Push migration to `dev`.
2. Validate API/page behavior and RLS in `dev`.
3. Push migration to `prod`.

Detailed rules: `docs/migration-release-rules.md`.
