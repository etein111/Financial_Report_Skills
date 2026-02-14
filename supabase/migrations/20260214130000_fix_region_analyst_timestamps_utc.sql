-- Fix timestamptz write semantics: store UTC in DB, convert to Asia/Shanghai on display layer.
--
-- Previous migration used timezone('Asia/Shanghai', now()) for timestamptz columns, which can
-- shift the actual stored instant (timestamptz expects an absolute time).

-- 1) Updated-at trigger should write UTC (timestamptz default behavior).
create or replace function public.set_updated_at_utc()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- 2) Region: defaults + trigger
alter table public.region
  alter column created_at set default now(),
  alter column updated_at set default now();

drop trigger if exists trg_region_updated_at on public.region;
create trigger trg_region_updated_at
before update on public.region
for each row execute function public.set_updated_at_utc();

-- 3) Analyst: defaults + trigger
alter table public.analyst
  alter column created_at set default now(),
  alter column updated_at set default now();

drop trigger if exists trg_analyst_updated_at on public.analyst;
create trigger trg_analyst_updated_at
before update on public.analyst
for each row execute function public.set_updated_at_utc();

-- Keep the old function around (if any local tooling references it); it is intentionally unused.
