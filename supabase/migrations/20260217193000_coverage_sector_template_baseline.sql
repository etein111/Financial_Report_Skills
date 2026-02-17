-- Baseline schema for coverage/sector/template management.
-- Includes: tables, constraints, indexes, updated_at triggers, and RLS policies.

create extension if not exists pgcrypto;

-- Keep same updated_at behavior as existing tables.
create or replace function public.set_updated_at_utc()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- sector
create table if not exists public.sector (
  id uuid primary key default gen_random_uuid(),
  level smallint not null check (level in (1, 2)),
  parent_id uuid references public.sector(id) on delete restrict,
  name_en text not null,
  name_cn text,
  wind_name text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint sector_level_parent_check check (
    (level = 1 and parent_id is null) or
    (level = 2 and parent_id is not null)
  )
);

create index if not exists idx_sector_level_parent on public.sector(level, parent_id);
create index if not exists idx_sector_name_en_lower on public.sector(lower(name_en));
create index if not exists idx_sector_active on public.sector(is_active);
create unique index if not exists uidx_sector_l1_name_en
  on public.sector(lower(name_en))
  where parent_id is null;
create unique index if not exists uidx_sector_l2_parent_name_en
  on public.sector(parent_id, lower(name_en))
  where parent_id is not null;

create or replace function public.validate_sector_hierarchy()
returns trigger
language plpgsql
as $$
declare
  v_parent_level smallint;
  v_parent_parent uuid;
begin
  if new.parent_id is not null and new.parent_id = new.id then
    raise exception 'sector parent cannot reference itself';
  end if;

  if new.level = 1 then
    if new.parent_id is not null then
      raise exception 'level 1 sector cannot have parent';
    end if;
    return new;
  end if;

  -- level=2: parent must exist and must be level=1.
  select s.level, s.parent_id
    into v_parent_level, v_parent_parent
  from public.sector s
  where s.id = new.parent_id;

  if not found then
    raise exception 'level 2 sector must reference an existing parent';
  end if;

  if v_parent_level <> 1 then
    raise exception 'level 2 sector parent must be level 1';
  end if;

  if v_parent_parent is not null then
    raise exception 'sector hierarchy supports only two levels';
  end if;

  return new;
end;
$$;

drop trigger if exists trg_sector_hierarchy on public.sector;
create trigger trg_sector_hierarchy
before insert or update on public.sector
for each row execute function public.validate_sector_hierarchy();

drop trigger if exists trg_sector_updated_at on public.sector;
create trigger trg_sector_updated_at
before update on public.sector
for each row execute function public.set_updated_at_utc();

-- coverage
create table if not exists public.coverage (
  id uuid primary key default gen_random_uuid(),
  ticker text not null,
  english_full_name text not null,
  chinese_short_name text,
  traditional_chinese text,
  sector_id uuid not null references public.sector(id) on delete restrict,
  isin text not null,
  country_of_domicile text not null,
  reporting_currency text,
  ads_conversion_factor numeric(18, 6) check (ads_conversion_factor > 0),
  is_duplicate boolean not null default false,
  approved_by uuid references auth.users(id) on delete set null,
  approved_at timestamptz,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists uidx_coverage_ticker_lower
  on public.coverage(lower(btrim(ticker)));
create unique index if not exists uidx_coverage_isin_upper
  on public.coverage(upper(btrim(isin)));
create index if not exists idx_coverage_sector on public.coverage(sector_id);
create index if not exists idx_coverage_name_lower on public.coverage(lower(english_full_name));
create index if not exists idx_coverage_updated_at_desc on public.coverage(updated_at desc);

drop trigger if exists trg_coverage_updated_at on public.coverage;
create trigger trg_coverage_updated_at
before update on public.coverage
for each row execute function public.set_updated_at_utc();

-- coverage_analyst
create table if not exists public.coverage_analyst (
  id uuid primary key default gen_random_uuid(),
  coverage_id uuid not null references public.coverage(id) on delete cascade,
  analyst_id uuid not null references public.analyst(id) on delete restrict,
  role smallint not null check (role between 1 and 4),
  sort_order smallint not null check (sort_order between 1 and 4),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint coverage_analyst_uniq_pair unique (coverage_id, analyst_id),
  constraint coverage_analyst_uniq_sort unique (coverage_id, sort_order)
);

create index if not exists idx_cov_analyst_coverage on public.coverage_analyst(coverage_id);
create index if not exists idx_cov_analyst_analyst on public.coverage_analyst(analyst_id);

create or replace function public.validate_coverage_analyst_limit()
returns trigger
language plpgsql
as $$
declare
  v_count int;
begin
  if tg_op = 'INSERT' then
    select count(*) into v_count
    from public.coverage_analyst
    where coverage_id = new.coverage_id;

    if v_count >= 4 then
      raise exception 'a coverage can have at most 4 analysts';
    end if;
    return new;
  end if;

  if tg_op = 'UPDATE' and new.coverage_id is distinct from old.coverage_id then
    select count(*) into v_count
    from public.coverage_analyst
    where coverage_id = new.coverage_id;

    if v_count >= 4 then
      raise exception 'a coverage can have at most 4 analysts';
    end if;
  end if;

  return new;
end;
$$;

drop trigger if exists trg_coverage_analyst_limit on public.coverage_analyst;
create trigger trg_coverage_analyst_limit
before insert or update on public.coverage_analyst
for each row execute function public.validate_coverage_analyst_limit();

drop trigger if exists trg_coverage_analyst_updated_at on public.coverage_analyst;
create trigger trg_coverage_analyst_updated_at
before update on public.coverage_analyst
for each row execute function public.set_updated_at_utc();

-- template
create table if not exists public.template (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  report_type text not null,
  file_type text not null check (file_type in ('word', 'excel')),
  file_path text not null,
  version integer not null check (version >= 1),
  is_active boolean not null default false,
  uploaded_by uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint template_uniq_version unique (report_type, file_type, version)
);

create unique index if not exists uidx_template_active_one
  on public.template(report_type, file_type)
  where is_active = true;
create index if not exists idx_template_group on public.template(report_type, file_type);
create index if not exists idx_template_created_at_desc on public.template(created_at desc);

drop trigger if exists trg_template_updated_at on public.template;
create trigger trg_template_updated_at
before update on public.template
for each row execute function public.set_updated_at_utc();

-- RLS
alter table public.sector enable row level security;
alter table public.coverage enable row level security;
alter table public.coverage_analyst enable row level security;
alter table public.template enable row level security;

drop policy if exists sector_select_authenticated on public.sector;
create policy sector_select_authenticated
on public.sector
for select
to authenticated
using (true);

drop policy if exists sector_write_admin on public.sector;
create policy sector_write_admin
on public.sector
for all
to authenticated
using ((auth.jwt()->'app_metadata'->>'role') = 'admin')
with check ((auth.jwt()->'app_metadata'->>'role') = 'admin');

drop policy if exists coverage_select_authenticated on public.coverage;
create policy coverage_select_authenticated
on public.coverage
for select
to authenticated
using (true);

drop policy if exists coverage_insert_admin_analyst on public.coverage;
create policy coverage_insert_admin_analyst
on public.coverage
for insert
to authenticated
with check ((auth.jwt()->'app_metadata'->>'role') in ('admin', 'analyst'));

drop policy if exists coverage_update_admin on public.coverage;
create policy coverage_update_admin
on public.coverage
for update
to authenticated
using ((auth.jwt()->'app_metadata'->>'role') = 'admin')
with check ((auth.jwt()->'app_metadata'->>'role') = 'admin');

drop policy if exists coverage_delete_admin on public.coverage;
create policy coverage_delete_admin
on public.coverage
for delete
to authenticated
using ((auth.jwt()->'app_metadata'->>'role') = 'admin');

drop policy if exists coverage_analyst_select_authenticated on public.coverage_analyst;
create policy coverage_analyst_select_authenticated
on public.coverage_analyst
for select
to authenticated
using (true);

drop policy if exists coverage_analyst_insert_admin_analyst on public.coverage_analyst;
create policy coverage_analyst_insert_admin_analyst
on public.coverage_analyst
for insert
to authenticated
with check ((auth.jwt()->'app_metadata'->>'role') in ('admin', 'analyst'));

drop policy if exists coverage_analyst_update_admin on public.coverage_analyst;
create policy coverage_analyst_update_admin
on public.coverage_analyst
for update
to authenticated
using ((auth.jwt()->'app_metadata'->>'role') = 'admin')
with check ((auth.jwt()->'app_metadata'->>'role') = 'admin');

drop policy if exists coverage_analyst_delete_admin on public.coverage_analyst;
create policy coverage_analyst_delete_admin
on public.coverage_analyst
for delete
to authenticated
using ((auth.jwt()->'app_metadata'->>'role') = 'admin');

drop policy if exists template_select_authenticated on public.template;
create policy template_select_authenticated
on public.template
for select
to authenticated
using (true);

drop policy if exists template_write_admin on public.template;
create policy template_write_admin
on public.template
for all
to authenticated
using ((auth.jwt()->'app_metadata'->>'role') = 'admin')
with check ((auth.jwt()->'app_metadata'->>'role') = 'admin');
