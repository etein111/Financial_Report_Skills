-- template_file_path / schema_file_path 补充 bucket 前缀（templates/）
-- 路径规则的唯一定义处在此文件，Python 侧不拼路径。

create or replace function public.get_template_storage_paths(
    p_report_type text,
    p_language    text
)
returns table (template_file_path text, schema_file_path text)
language sql stable security definer
as $$
    select
        'templates/' || p_report_type || '/' || p_language || '/template.docx' as template_file_path,
        'templates/' || p_report_type || '/' || p_language || '/schema.yaml'    as schema_file_path;
$$;

comment on function public.get_template_storage_paths is
'返回指定 report_type + language 对应的模板 Storage 路径（含 bucket 前缀）。路径规则的唯一定义处。';

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
    v_template_path := 'templates/' || p_report_type || '/' || p_language || '/template.docx';
    v_schema_path   := 'templates/' || p_report_type || '/' || p_language || '/schema.yaml';

    insert into public.report_template (id, report_type, language, template_file_path, schema_file_path)
    values (v_id, p_report_type, p_language, v_template_path, v_schema_path)
    on conflict (id) do update
        set template_file_path = excluded.template_file_path,
            schema_file_path   = excluded.schema_file_path;
end;
$$;

comment on function public.upsert_template_record is
'上传文件后调用，服务端按固定规则生成路径（含 bucket 前缀）并 upsert report_template 记录。';

-- 修复存量记录（去掉重复前缀保护，幂等）
update public.report_template
set
    template_file_path = 'templates/' || template_file_path,
    schema_file_path   = case
        when schema_file_path is not null and schema_file_path != ''
        then 'templates/' || schema_file_path
        else schema_file_path
    end
where template_file_path not like 'templates/%';
