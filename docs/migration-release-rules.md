# Supabase Migration Release Rules

## Release Order

1. Apply and verify in `dev` first.
2. Apply in `prod` after dev verification succeeds.

## Migration Source Of Truth

- All schema/policy/function changes must live in `supabase/migrations/*.sql`.
- Seed data must live in `supabase/seed/*.sql`.
- Do not create a custom migration version table.
- Incremental execution is managed by Supabase built-in table: `supabase_migrations.schema_migrations`.

## Verification Command

```sql
select version, name, statements, created_by
from supabase_migrations.schema_migrations
order by version desc;
```

## Emergency Dashboard Changes

- Dashboard direct SQL is only for emergency use.
- Any emergency change must be backfilled into a migration SQL file and committed to Git on the same day.
- Production should not keep undocumented Dashboard-only drift.
