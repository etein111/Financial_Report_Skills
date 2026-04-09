-- 20260409000630_060_coverage_functions.sql
-- coverage 解析与创建 RPC；resolve_analyst_by_email 错误消息改为中文

-- ----------------------------------------------------------------
-- 补丁：resolve_analyst_by_email 错误消息改为中文
-- ----------------------------------------------------------------

create or replace function public.resolve_analyst_by_email(
    p_email text
)
returns public.analyst
language plpgsql stable security definer
as $$
declare
    v_email  text;
    v_record public.analyst%rowtype;
begin
    v_email := lower(trim(p_email));

    select * into v_record
    from public.analyst
    where email = v_email;

    if not found then
        raise exception '找不到分析师：%', p_email;
    end if;

    if not coalesce(v_record.is_active, true) then
        raise exception '分析师已停用：%', p_email;
    end if;

    return v_record;
end;
$$;

comment on function public.resolve_analyst_by_email is
'根据邮箱查询 analyst 记录。自动 lowercase/trim，不存在或 is_active=false 时抛出中文异常。';

revoke execute on function public.resolve_analyst_by_email(text) from public, anon;
grant execute on function public.resolve_analyst_by_email(text) to authenticated;

-- ----------------------------------------------------------------
-- resolve_coverage
-- ----------------------------------------------------------------

create or replace function public.resolve_coverage(
    p_ticker        text,
    p_analyst_email text
)
returns table(coverage_id uuid)
language plpgsql stable security definer
as $$
declare
    v_ticker text;
    v_email  text;
    v_id     uuid;
begin
    v_ticker := lower(btrim(p_ticker));
    v_email  := lower(btrim(p_analyst_email));

    select c.id into v_id
    from public.coverage c
    join public.coverage_analyst ca on ca.coverage_id = c.id
    where lower(btrim(c.ticker))         = v_ticker
      and lower(btrim(ca.analyst_email)) = v_email;

    if not found then
        raise exception '未找到匹配的 Coverage（ticker=''%''，分析师=''%''）。请先创建 Coverage。',
            p_ticker, p_analyst_email;
    end if;

    return query select v_id;
end;
$$;

comment on function public.resolve_coverage is
'按 ticker + 分析师邮箱查询唯一 coverage。未命中时抛出中文异常，提示创建 Coverage。';

revoke execute on function public.resolve_coverage from public, anon;
grant execute on function public.resolve_coverage to authenticated;

-- ----------------------------------------------------------------
-- create_coverage
-- ----------------------------------------------------------------

create or replace function public.create_coverage(
    p_ticker              text,
    p_english_name        text,
    p_sector_id           uuid,
    p_isin                text,
    p_country_of_domicile text,
    p_analysts            jsonb,
    p_chinese_name        text default null,
    p_traditional_chinese text default null
)
returns table(coverage_id uuid)
language plpgsql security definer
as $$
declare
    v_coverage_id uuid;
    v_analyst     jsonb;
    v_email       text;
    v_order       integer;
begin
    if p_analysts is null or jsonb_array_length(p_analysts) = 0 then
        raise exception 'p_analysts 不能为空，Coverage 必须至少关联一名分析师。';
    end if;

    begin
        insert into public.coverage (
            ticker, english_name, chinese_name, traditional_chinese,
            sector_id, isin, country_of_domicile
        ) values (
            p_ticker,
            p_english_name,
            p_chinese_name,
            p_traditional_chinese,
            p_sector_id,
            upper(btrim(p_isin)),
            p_country_of_domicile
        )
        returning id into v_coverage_id;
    exception
        when unique_violation then
            raise exception 'Coverage 已存在：ticker=''%'' 或 isin=''%'' 已被占用。',
                p_ticker, p_isin;
    end;

    for v_analyst in select * from jsonb_array_elements(p_analysts)
    loop
        v_email := lower(btrim(v_analyst->>'analyst_email'));
        v_order := (v_analyst->>'author_order')::integer;

        if v_email is null or v_email = '' then
            raise exception 'analysts 条目缺少有效的 analyst_email：%', v_analyst;
        end if;
        if v_analyst->>'author_order' is null then
            raise exception 'analysts 条目缺少 author_order 字段：%', v_analyst;
        end if;

        insert into public.coverage_analyst (coverage_id, analyst_email, author_order)
        values (v_coverage_id, v_email, v_order);
    end loop;

    return query select v_coverage_id;
end;
$$;

comment on function public.create_coverage is
'创建 coverage 及初始 coverage_analyst 关系。ticker/isin 冲突时抛出中文异常。';

revoke execute on function public.create_coverage from public, anon;
grant execute on function public.create_coverage to authenticated;
