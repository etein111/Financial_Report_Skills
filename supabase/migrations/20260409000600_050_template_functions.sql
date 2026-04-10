-- 20260409000600_050_template_functions.sql
-- Template Storage 路径规则（唯一定义处）+ 模板记录管理 RPC

create or replace function public.get_template_storage_paths(
    p_report_type text,
    p_language    text
)
returns table (template_file_path text, schema_file_path text)
language sql stable security definer
as $$
    select
        p_report_type || '/' || p_language || '/template.docx' as template_file_path,
        p_report_type || '/' || p_language || '/schema.yaml'    as schema_file_path;
$$;

comment on function public.get_template_storage_paths is
'返回指定 report_type + language 对应的模板 Storage 路径。路径规则的唯一定义处。';

-- ----------------------------------------------------------------

create or replace function public.upsert_template_record(
    p_report_type text,
    p_language    text
)
returns void
language plpgsql security definer
as $$
declare
    v_id                text;
    v_template_path     text;
    v_schema_path       text;
begin
    v_id            := p_report_type || '_' || p_language;
    v_template_path := p_report_type || '/' || p_language || '/template.docx';
    v_schema_path   := p_report_type || '/' || p_language || '/schema.yaml';

    insert into public.report_template (id, report_type, language, template_file_path, schema_file_path)
    values (v_id, p_report_type, p_language, v_template_path, v_schema_path)
    on conflict (id) do update
        set template_file_path = excluded.template_file_path,
            schema_file_path   = excluded.schema_file_path;
end;
$$;

comment on function public.upsert_template_record is
'上传文件后调用，服务端按固定规则生成路径并 upsert report_template 记录。';

-- ----------------------------------------------------------------

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
        raise exception 'Cannot reuse self: report_type=''%''', p_report_type;
    end if;

    select * into v_source
    from public.report_template
    where id = p_same_as_report_type || '_' || p_language;

    if not found then
        raise exception 'Source template not found: ''%''',
            p_same_as_report_type || '_' || p_language;
    end if;

    if v_source.template_file_path = '' or v_source.template_file_path is null then
        raise exception 'Source template not published (empty path): ''%''',
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

comment on function public.reuse_template is
'让 report_type 的模板记录复用 same_as_report_type 的文件路径（静态复制）。';

-- ----------------------------------------------------------------
-- 权限

revoke execute on function public.upsert_template_record from public, anon, authenticated;
grant execute on function public.upsert_template_record to authenticated;

revoke execute on function public.reuse_template from public, anon, authenticated;
grant execute on function public.reuse_template to authenticated;

revoke execute on function public.get_template_storage_paths from public, anon;
grant execute on function public.get_template_storage_paths to authenticated;
