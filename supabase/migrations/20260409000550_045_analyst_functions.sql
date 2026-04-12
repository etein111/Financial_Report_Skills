-- 20260409000550_045_analyst_functions.sql
-- Analyst 查询 RPC：将 is_active 校验逻辑封装在服务端，Python 端只做 RPC 调用

create or replace function public.resolve_analyst_by_email(
    p_email text
)
returns public.analyst
language plpgsql stable security definer
as $$
declare
    v_email text;
    v_record public.analyst%rowtype;
begin
    v_email := lower(trim(p_email));

    select * into v_record
    from public.analyst
    where email = v_email;

    if not found then
        raise exception 'Analyst not found: %', p_email;
    end if;

    if not coalesce(v_record.is_active, true) then
        raise exception 'Analyst is inactive: %', p_email;
    end if;

    return v_record;
end;
$$;

comment on function public.resolve_analyst_by_email is
'根据邮箱查询 analyst 记录。自动 lowercase/trim，不存在或 is_active=false 时抛出异常。';

-- RLS：所有已认证用户可调用（与 analyst 表的 dict_select 策略对齐）
revoke execute on function public.resolve_analyst_by_email from public, anon;
grant execute on function public.resolve_analyst_by_email to authenticated;
