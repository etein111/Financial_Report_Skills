-- 1. get_template_storage_paths: 去掉 SECURITY DEFINER（纯计算，不读写表）
CREATE OR REPLACE FUNCTION "public"."get_template_storage_paths"("p_report_type" "text", "p_language" "text") RETURNS TABLE("template_file_path" "text", "schema_file_path" "text")
    LANGUAGE "sql" STABLE
    AS $$
    select
        'templates/' || p_report_type || '/' || p_language || '/template.docx' as template_file_path,
        'templates/' || p_report_type || '/' || p_language || '/schema.yaml'    as schema_file_path;
$$;

-- 2. resolve_coverage: 去掉 SECURITY DEFINER（只读表，SELECT RLS = USING(true)）
CREATE OR REPLACE FUNCTION "public"."resolve_coverage"("p_ticker" "text", "p_analyst_email" "text") RETURNS TABLE("coverage_id" "uuid")
    LANGUAGE "plpgsql" STABLE
    AS $$
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

-- 3. reuse_template: 去掉 SECURITY DEFINER + 提取 v_source_id 变量
CREATE OR REPLACE FUNCTION "public"."reuse_template"("p_report_type" "text", "p_language" "text", "p_same_as_report_type" "text") RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
declare
    v_source    public.report_template%rowtype;
    v_source_id text;
    v_target_id text;
begin
    if p_report_type = p_same_as_report_type then
        raise exception '不能复用自身：report_type=''%''', p_report_type;
    end if;

    v_source_id := p_same_as_report_type || '_' || p_language;

    select * into v_source
    from public.report_template
    where id = v_source_id;

    if not found then
        raise exception '源模板未找到：''%''', v_source_id;
    end if;

    if v_source.template_file_path = '' or v_source.template_file_path is null then
        raise exception '源模板未发布（路径为空）：''%''', v_source_id;
    end if;

    v_target_id := p_report_type || '_' || p_language;

    insert into public.report_template (id, report_type, language, template_file_path, schema_file_path)
    values (v_target_id, p_report_type, p_language, v_source.template_file_path, v_source.schema_file_path)
    on conflict (id) do update
        set template_file_path = excluded.template_file_path,
            schema_file_path   = excluded.schema_file_path;
end;
$$;

-- 4. upsert_template_record: 去掉 SECURITY DEFINER
CREATE OR REPLACE FUNCTION "public"."upsert_template_record"("p_report_type" "text", "p_language" "text") RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
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
