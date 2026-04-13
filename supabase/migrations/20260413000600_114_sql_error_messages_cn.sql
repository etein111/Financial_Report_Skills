-- 20260413000600_114_sql_error_messages_cn.sql
-- 统一 SQL 函数 raise exception 消息为中文
-- 受影响函数：validate_sector_hierarchy, report_enforce_status_transition,
--             resolve_analyst_by_email, reuse_template

-- ===================================================================
-- 1. validate_sector_hierarchy：5 处英文 → 中文
-- ===================================================================

create or replace function public.validate_sector_hierarchy()
returns trigger
language plpgsql
as $$
declare
  v_parent_level smallint;
  v_parent_parent uuid;
begin
  if new.parent_id is not null and new.parent_id = new.id then
    raise exception 'sector 父级不能引用自身';
  end if;

  if new.level = 1 then
    if new.parent_id is not null then
      raise exception '一级行业不能设置父级';
    end if;
    return new;
  end if;

  select s.level, s.parent_id
    into v_parent_level, v_parent_parent
  from public.sector s
  where s.id = new.parent_id;

  if not found then
    raise exception '二级行业必须引用已存在的父级';
  end if;

  if v_parent_level <> 1 then
    raise exception '二级行业的父级必须是一级行业';
  end if;

  if v_parent_parent is not null then
    raise exception '行业层级最多支持两级';
  end if;

  return new;
end;
$$;

-- ===================================================================
-- 2. report_enforce_status_transition：1 处英文 → 中文
-- ===================================================================

create or replace function public.report_enforce_status_transition()
returns trigger
language plpgsql
as $$
begin
  if tg_op = 'UPDATE' and new.status is distinct from old.status then
    if not public.report_status_is_valid(old.status, new.status) then
      raise exception '无效的报告状态转换：% → %', old.status, new.status;
    end if;
  end if;
  return new;
end;
$$;

-- ===================================================================
-- 3. resolve_analyst_by_email：2 处英文 → 中文
--    基于 105 版本（无 SECURITY DEFINER），保持属性不变
-- ===================================================================

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
        raise exception '找不到分析师：%', p_email;
    end if;

    if not coalesce(v_record.is_active, true) then
        raise exception '分析师已停用：%', p_email;
    end if;

    return v_record;
end;
$$;

-- ===================================================================
-- 4. reuse_template：3 处英文 → 中文
-- ===================================================================

create or replace function public.reuse_template(
    p_report_type         text,
    p_language            text,
    p_same_as_report_type text
)
returns void
language plpgsql security definer
as $$
declare
    v_source    public.report_template%rowtype;
    v_target_id text;
begin
    if p_report_type = p_same_as_report_type then
        raise exception '不能复用自身：report_type=''%''', p_report_type;
    end if;

    select * into v_source
    from public.report_template
    where id = p_same_as_report_type || '_' || p_language;

    if not found then
        raise exception '源模板未找到：''%''',
            p_same_as_report_type || '_' || p_language;
    end if;

    if v_source.template_file_path = '' or v_source.template_file_path is null then
        raise exception '源模板未发布（路径为空）：''%''',
            p_same_as_report_type || '_' || p_language;
    end if;

    v_target_id := p_report_type || '_' || p_language;

    insert into public.report_template (id, report_type, language, template_file_path, schema_file_path)
    values (v_target_id, p_report_type, p_language, v_source.template_file_path, v_source.schema_file_path)
    on conflict (id) do update
        set template_file_path = excluded.template_file_path,
            schema_file_path   = excluded.schema_file_path;
end;
$$;
