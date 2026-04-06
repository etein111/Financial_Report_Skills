-- Supabase public schema DDL snapshot
-- Generated at: 2026-04-06T06:14:24.426640Z
-- Source: http://47.57.213.88/rest/v1/ OpenAPI definitions
-- Note: This file is inferred from the live PostgREST schema description.
-- Note: Defaults and NOT NULL flags are preserved when exposed by OpenAPI.
-- Note: Foreign keys, indexes, unique constraints, check constraints, triggers, and RLS policies are not fully exposed by /rest/v1/ and are therefore omitted here unless directly inferable.
-- Note: Alibaba Cloud / RDS / embedding-related auxiliary tables are intentionally excluded.
-- Note: This snapshot reflects the live database as of generation time. Where current design docs have evolved beyond the live schema, keep this file as live-state truth rather than rewriting DDL to match target design.

create table if not exists public.region (
  id uuid primary key not null default gen_random_uuid(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  name_en text not null,
  name_cn text not null,
  code text not null,
  is_active boolean not null default true
);

create table if not exists public.analyst (
  id uuid primary key not null default gen_random_uuid(),
  full_name text not null,
  chinese_name text,
  email public.citext not null,
  suffix text,
  sfc text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  region_code text
);

create table if not exists public.sector (
  id uuid primary key not null default gen_random_uuid(),
  level smallint not null,
  parent_id uuid,
  name_en text not null,
  name_cn text,
  wind_name text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.coverage (
  id uuid primary key not null default gen_random_uuid(),
  ticker text not null,
  english_full_name text not null,
  chinese_short_name text,
  traditional_chinese text,
  sector_id uuid not null,
  isin text not null,
  country_of_domicile text not null,
  reporting_currency text,
  ads_conversion_factor numeric,
  is_duplicate boolean not null default false,
  approved_by uuid,
  approved_at timestamptz,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  index_code text
);

create table if not exists public.coverage_analyst (
  id uuid primary key not null default gen_random_uuid(),
  coverage_id uuid not null,
  analyst_id uuid not null,
  role smallint not null,
  sort_order smallint not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.rating (
  id uuid primary key not null default gen_random_uuid(),
  name text not null,
  code text not null,
  sort integer not null default 1,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.report_type (
  id uuid primary key not null default gen_random_uuid(),
  name text not null,
  code text not null,
  sort integer not null default 1,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists public.template (
  -- Live schema: template records are keyed by report_type + language.
  -- Assets are defined by the Word template file and its paired schema.yaml.
  -- Note: multiple report_type records may point to the same template_file_path/schema_file_path when reports share one template asset.
  id uuid primary key not null default gen_random_uuid(),
  name text not null,
  report_type text not null,
  template_file_path text not null,
  uploaded_by uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  language text not null default 'en',
  schema_file_path text
);

create table if not exists public.report (
  id uuid primary key not null default gen_random_uuid(),
  owner_user_id uuid not null,
  title text not null,
  report_type text not null,
  status text not null default 'draft',
  current_version_no integer not null default 0,
  coverage_id uuid,
  sector_id uuid,
  published_by uuid,
  published_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  ticker text,
  rating text,
  target_price numeric,
  report_language text,
  investment_thesis text,
  certificate_confirmed boolean not null default false,
  contact_person_id uuid,
  region_code text
);

create table if not exists public.report_analyst (
  id uuid primary key not null default gen_random_uuid(),
  report_id uuid not null,
  analyst_id uuid not null,
  role smallint not null,
  sort_order smallint not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.report_version (
  id uuid primary key not null default gen_random_uuid(),
  report_id uuid not null,
  version_no integer not null,
  snapshot_json jsonb not null,
  word_file_path text,
  model_file_path text,
  changed_by uuid not null,
  changed_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  word_file_name text,
  model_file_name text,
  pdf_file_path text,
  pdf_file_name text
);

create table if not exists public.report_status_log (
  id uuid primary key not null default gen_random_uuid(),
  report_id uuid not null,
  from_status text not null,
  to_status text not null,
  action_by uuid not null,
  action_at timestamptz not null default now(),
  reason text,
  version_no integer not null,
  created_at timestamptz not null default now(),
  action_by_name text
);

create table if not exists public.chief_approve (
  id uuid primary key not null default gen_random_uuid(),
  report_id uuid not null,
  file_path text not null,
  file_name text not null,
  file_type text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.rqc_approve (
  id uuid primary key not null default gen_random_uuid(),
  report_id uuid not null,
  file_path text not null,
  file_name text not null,
  file_type text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.report_push_log (
  id uuid primary key not null default gen_random_uuid(),
  report_id uuid not null,
  status text not null,
  http_status_code integer,
  response_body text,
  error_message text,
  payload_sent jsonb,
  trigger_type text not null,
  triggered_by uuid not null,
  created_at timestamptz not null default now()
);
