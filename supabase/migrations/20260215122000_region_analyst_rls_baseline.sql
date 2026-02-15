-- Baseline schema for region/analyst + RLS (UTC timestamptz semantics).

-- Extensions
create extension if not exists pgcrypto;
create extension if not exists citext;

-- updated_at trigger (UTC)
create or replace function public.set_updated_at_utc()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- Region
create table if not exists public.region (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  code text not null unique,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_region_created_at_desc on public.region (created_at desc);

drop trigger if exists trg_region_updated_at on public.region;
create trigger trg_region_updated_at
before update on public.region
for each row execute function public.set_updated_at_utc();

-- Analyst
create table if not exists public.analyst (
  id uuid primary key default gen_random_uuid(),
  full_name text not null,
  chinese_name text,
  email citext not null unique,
  region_id uuid references public.region(id) on delete set null,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_analyst_created_at_desc on public.analyst (created_at desc);
create index if not exists idx_analyst_full_name on public.analyst (full_name);
create index if not exists idx_analyst_chinese_name on public.analyst (chinese_name);
create index if not exists idx_analyst_email on public.analyst (email);

drop trigger if exists trg_analyst_updated_at on public.analyst;
create trigger trg_analyst_updated_at
before update on public.analyst
for each row execute function public.set_updated_at_utc();

-- RLS
alter table public.region enable row level security;
alter table public.analyst enable row level security;

drop policy if exists region_select_authenticated on public.region;
create policy region_select_authenticated
on public.region
for select
to authenticated
using (true);

drop policy if exists region_write_admin on public.region;
create policy region_write_admin
on public.region
for all
to authenticated
using ((auth.jwt()->'app_metadata'->>'role') = 'admin')
with check ((auth.jwt()->'app_metadata'->>'role') = 'admin');

drop policy if exists analyst_select_authenticated on public.analyst;
create policy analyst_select_authenticated
on public.analyst
for select
to authenticated
using (true);

drop policy if exists analyst_write_admin on public.analyst;
create policy analyst_write_admin
on public.analyst
for all
to authenticated
using ((auth.jwt()->'app_metadata'->>'role') = 'admin')
with check ((auth.jwt()->'app_metadata'->>'role') = 'admin');

