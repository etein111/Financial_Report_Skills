# Backend

## Run

```bash
uv sync
uv run uvicorn src.main:app --reload --port 8000
```

## Environment

开发环境直接使用仓库内的 `backend/.env`（已提交 Git）：

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_PASSWORD_RESET_REDIRECT`
