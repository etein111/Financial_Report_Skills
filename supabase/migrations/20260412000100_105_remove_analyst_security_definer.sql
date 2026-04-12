-- 20260412000100_105_remove_analyst_security_definer.sql
-- 移除 resolve_analyst_by_email 的 SECURITY DEFINER
-- analyst 表的 dict_select RLS 已对所有已认证用户放通 (using true)，SECURITY DEFINER 无实际作用

create or replace function public.resolve_analyst_by_email(
    p_email text
)
returns public.analyst
language plpgsql stable
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
