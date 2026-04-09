create schema if not exists extensions;

create extension if not exists pgcrypto with schema extensions;

alter database postgres set timezone to 'Asia/Shanghai';

create or replace function public.current_app_role()
returns text
language sql
stable
as $$
  select coalesce(auth.jwt()->'app_metadata'->>'role', '');
$$;

comment on function public.current_app_role() is '获取当前认证用户的 app_metadata 中的 role 字段值。用于 RLS 策略中判断当前用户的业务角色（admin/sa/analyst）。返回 text，未登录或无 role 时返回空字符串。';

create or replace function public.report_status_is_valid(from_status text, to_status text)
returns boolean
language sql
immutable
as $$
  select (
    (from_status = 'draft' and to_status = 'submitted')
    or (from_status = 'submitted' and to_status in ('published', 'rejected'))
    or (from_status = 'rejected' and to_status = 'draft')
  );
$$;

comment on function public.report_status_is_valid(text, text) is '判断报告状态流转是否合法（IMMUTABLE）。合法路径：draft→submitted、submitted→published、submitted→rejected、rejected→draft。其他任何组合均返回 false。';

create or replace function public.set_updated_at_utc()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

comment on function public.set_updated_at_utc() is '通用 BEFORE UPDATE 触发器函数，将 NEW.updated_at 设为当前 UTC 时间（now()）。被所有含 updated_at 字段的表的 trg_*_updated_at 触发器调用。';
