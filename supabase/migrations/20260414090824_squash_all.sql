


SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


CREATE SCHEMA IF NOT EXISTS "public";


ALTER SCHEMA "public" OWNER TO "pg_database_owner";


COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE OR REPLACE FUNCTION "public"."create_coverage"("p_ticker" "text", "p_english_name" "text", "p_sector_id" "uuid", "p_isin" "text", "p_country_of_domicile" "text", "p_analysts" "jsonb", "p_chinese_name" "text" DEFAULT NULL::"text", "p_traditional_chinese" "text" DEFAULT NULL::"text") RETURNS TABLE("coverage_id" "uuid")
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
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


ALTER FUNCTION "public"."create_coverage"("p_ticker" "text", "p_english_name" "text", "p_sector_id" "uuid", "p_isin" "text", "p_country_of_domicile" "text", "p_analysts" "jsonb", "p_chinese_name" "text", "p_traditional_chinese" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."create_coverage"("p_ticker" "text", "p_english_name" "text", "p_sector_id" "uuid", "p_isin" "text", "p_country_of_domicile" "text", "p_analysts" "jsonb", "p_chinese_name" "text", "p_traditional_chinese" "text") IS '创建 coverage 及初始 coverage_analyst 关系。ticker/isin 冲突时抛出中文异常。';



CREATE OR REPLACE FUNCTION "public"."current_app_role"() RETURNS "text"
    LANGUAGE "sql" STABLE
    AS $$
  select coalesce(auth.jwt()->'app_metadata'->>'role', '');
$$;


ALTER FUNCTION "public"."current_app_role"() OWNER TO "postgres";


COMMENT ON FUNCTION "public"."current_app_role"() IS '获取当前认证用户的 app_metadata 中的 role 字段值。用于 RLS 策略中判断当前用户的业务角色（admin/sa/analyst）。返回 text，未登录或无 role 时返回空字符串。';



CREATE OR REPLACE FUNCTION "public"."generate_upload_path"("p_report_id" "uuid", "p_file_category" "text") RETURNS "text"
    LANGUAGE "plpgsql"
    AS $$
declare
    v_status    text;
    v_timestamp text;
begin
    if p_file_category not in ('report', 'model') then
        raise exception 'file_category 非法：%，仅支持 report/model', p_file_category;
    end if;

    select status
      into v_status
      from public.report
     where id = p_report_id;

    if not found then
        raise exception '报告不存在: %', p_report_id;
    end if;

    if v_status not in ('draft', 'rejected') then
        raise exception '报告状态为 %，仅 draft/rejected 可生成上传路径', v_status;
    end if;

    v_timestamp := to_char(now(), 'YYYYMMDD_HH24MISS');
    return format('reports/%s/%s/%s/', p_report_id, p_file_category, v_timestamp);
end;
$$;


ALTER FUNCTION "public"."generate_upload_path"("p_report_id" "uuid", "p_file_category" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."generate_upload_path"("p_report_id" "uuid", "p_file_category" "text") IS '按 reports/{report_id}/{category}/{timestamp}/ 规则生成上传目录前缀。';



CREATE OR REPLACE FUNCTION "public"."get_template_storage_paths"("p_report_type" "text", "p_language" "text") RETURNS TABLE("template_file_path" "text", "schema_file_path" "text")
    LANGUAGE "sql" STABLE SECURITY DEFINER
    AS $$
    select
        'templates/' || p_report_type || '/' || p_language || '/template.docx' as template_file_path,
        'templates/' || p_report_type || '/' || p_language || '/schema.yaml'    as schema_file_path;
$$;


ALTER FUNCTION "public"."get_template_storage_paths"("p_report_type" "text", "p_language" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."get_template_storage_paths"("p_report_type" "text", "p_language" "text") IS '返回指定 report_type + language 对应的模板 Storage 路径（含 bucket 前缀）。路径规则的唯一定义处。';



CREATE OR REPLACE FUNCTION "public"."list_coverage_history"("p_ticker" "text", "p_analyst_email" "text") RETURNS TABLE("report_id" "uuid", "title" "text", "rating" "text", "target_price" numeric, "published_at" timestamp with time zone)
    LANGUAGE "plpgsql" STABLE
    AS $$
declare
    v_coverage_id uuid;
begin
    select rc.coverage_id
    into v_coverage_id
    from public.resolve_coverage(p_ticker, p_analyst_email) rc;

    return query
    select
        r.id as report_id,
        r.title,
        r.rating,
        r.target_price,
        r.published_at
    from public.report r
    where r.coverage_id = v_coverage_id
      and r.status = 'published'
    order by r.published_at desc nulls last, r.id desc;
end;
$$;


ALTER FUNCTION "public"."list_coverage_history"("p_ticker" "text", "p_analyst_email" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."list_coverage_history"("p_ticker" "text", "p_analyst_email" "text") IS '按 ticker + 1作分析师邮箱定位 coverage，返回已发布历史报告（report_id/title/rating/target_price/published_at）。coverage 存在但无历史时返回空列表。';



CREATE OR REPLACE FUNCTION "public"."report_enforce_status_transition"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
begin
  if tg_op = 'UPDATE' and new.status is distinct from old.status then
    if not public.report_status_is_valid(old.status, new.status) then
      raise exception '无效的报告状态转换：% → %', old.status, new.status;
    end if;
  end if;
  return new;
end;
$$;


ALTER FUNCTION "public"."report_enforce_status_transition"() OWNER TO "postgres";


COMMENT ON FUNCTION "public"."report_enforce_status_transition"() IS '报告状态流转强制校验触发器函数（BEFORE UPDATE）。当 report.status 发生变化时，调用 report_status_is_valid() 校验流转合法性，非法时抛出异常阻止写入。由 trg_report_status_transition 触发器绑定到 report 表。';



CREATE OR REPLACE FUNCTION "public"."report_status_is_valid"("from_status" "text", "to_status" "text") RETURNS boolean
    LANGUAGE "sql" IMMUTABLE
    AS $$
    select (from_status = 'draft' and to_status = 'submitted')
        or (from_status = 'submitted' and to_status in ('published', 'rejected', 'draft'))
        or (from_status = 'rejected' and to_status = 'draft')
$$;


ALTER FUNCTION "public"."report_status_is_valid"("from_status" "text", "to_status" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."report_status_is_valid"("from_status" "text", "to_status" "text") IS '判断报告状态流转是否合法（IMMUTABLE）。

合法路径：
  draft → submitted          （analyst 提交审阅）
  submitted → published      （sa 发布）
  submitted → rejected       （sa 退回）
  submitted → draft          （analyst 撤回，由 retract_report RPC 调用）
  rejected → draft           （analyst 撤回，由 retract_report RPC 调用）

所有其他路径均为非法，report_enforce_status_transition 触发器会在
UPDATE report 时调用本函数进行校验，非法流转将抛出异常。';



CREATE OR REPLACE FUNCTION "public"."report_write_status_log"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
declare
    v_metadata jsonb;
begin
    if new.status is distinct from old.status then
        v_metadata := jsonb_build_object(
            'title',              new.title,
            'report_type',        new.report_type,
            'lead_analyst_email', new.lead_analyst_email,
            'analyst_emails',     new.analyst_emails,
            'coverage_id',        new.coverage_id,
            'ticker',             new.ticker,
            'sector_id',          new.sector_id,
            'region_code',        new.region_code,
            'rating',             new.rating,
            'target_price',       new.target_price,
            'investment_thesis',  new.investment_thesis,
            'report_language',    new.report_language,
            'contact_person',     new.contact_person,
            'word_path',          new.word_path,
            'pdf_path',           new.pdf_path,
            'model_path',         new.model_path
        );

        insert into public.report_status_log (
            report_id, from_status, to_status,
            action_by, action_by_name, reason, metadata
        ) values (
            new.id, old.status, new.status,
            auth.uid(), auth.jwt()->>'email',
            case when new.status = 'rejected' then new.rejection_reason else null end,
            v_metadata
        );
    end if;

    return null;
end;
$$;


ALTER FUNCTION "public"."report_write_status_log"() OWNER TO "postgres";


COMMENT ON FUNCTION "public"."report_write_status_log"() IS 'AFTER UPDATE 触发器函数：当 report.status 变化时自动写入 report_status_log，metadata 直接记录 report 当前文件路径。';


SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."analyst" (
    "english_name" "text" NOT NULL,
    "chinese_name" "text",
    "email" "text" NOT NULL,
    "suffix" "text",
    "sfc" "text",
    "region_code" "text",
    "is_active" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "analyst_email_lowercase_check" CHECK (("email" = "lower"("email")))
);


ALTER TABLE "public"."analyst" OWNER TO "postgres";


COMMENT ON TABLE "public"."analyst" IS '分析师业务信息表。存储分析师的姓名、邮箱、所属区域、资质证书等信息，与 auth.users 解耦——认证信息由 Supabase Auth 管理，业务属性在此表维护。通过 email 字段（小写）与 auth.users.email 逻辑关联。';



COMMENT ON COLUMN "public"."analyst"."english_name" IS '分析师英文全名，如 "John Smith"';



COMMENT ON COLUMN "public"."analyst"."chinese_name" IS '分析师中文姓名';



COMMENT ON COLUMN "public"."analyst"."email" IS '分析师邮箱（唯一）。强制小写存储（CHECK 约束 email = lower(email)）。作为与 auth.users 的逻辑关联键，也用于 coverage_analyst.analyst_email 的关联';



COMMENT ON COLUMN "public"."analyst"."suffix" IS '姓名后缀/头衔，如 "CFA"、"FRM"';



COMMENT ON COLUMN "public"."analyst"."sfc" IS '证券期货从业资格编号（中国证监会 SFC 编号）';



COMMENT ON COLUMN "public"."analyst"."region_code" IS '分析师所属区域编码，引用 region.code，如 CN、HK';



COMMENT ON COLUMN "public"."analyst"."is_active" IS '是否在职。true=在职，false=已离职或停用';



COMMENT ON COLUMN "public"."analyst"."created_at" IS '记录创建时间（UTC）';



COMMENT ON COLUMN "public"."analyst"."updated_at" IS '记录最后更新时间（UTC），由 trg_analyst_updated_at 触发器自动维护';



CREATE OR REPLACE FUNCTION "public"."resolve_analyst_by_email"("p_email" "text") RETURNS "public"."analyst"
    LANGUAGE "plpgsql" STABLE
    AS $$
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


ALTER FUNCTION "public"."resolve_analyst_by_email"("p_email" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."resolve_analyst_by_email"("p_email" "text") IS '根据邮箱查询 analyst 记录。自动 lowercase/trim，不存在或 is_active=false 时抛出异常。';



CREATE OR REPLACE FUNCTION "public"."resolve_coverage"("p_ticker" "text", "p_analyst_email" "text") RETURNS TABLE("coverage_id" "uuid")
    LANGUAGE "plpgsql" STABLE SECURITY DEFINER
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


ALTER FUNCTION "public"."resolve_coverage"("p_ticker" "text", "p_analyst_email" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."resolve_coverage"("p_ticker" "text", "p_analyst_email" "text") IS '按 ticker + 分析师邮箱查询唯一 coverage。未命中时抛出中文异常，提示创建 Coverage。';



CREATE OR REPLACE FUNCTION "public"."retract_report"("p_report_id" "uuid") RETURNS TABLE("report_id" "uuid", "status" "text")
    LANGUAGE "plpgsql"
    AS $$
declare
    v_current_status text;
begin
    select r.status
      into v_current_status
      from public.report r
     where r.id = p_report_id;

    if not found then
        raise exception '报告不存在: %', p_report_id;
    end if;

    if v_current_status not in ('submitted', 'rejected') then
        raise exception '报告状态为 %，无法撤回（仅 submitted/rejected 可撤回）', v_current_status;
    end if;

    update public.report
       set status = 'draft',
           rejection_reason = null
     where id = p_report_id;

    return query select p_report_id, 'draft'::text;
end;
$$;


ALTER FUNCTION "public"."retract_report"("p_report_id" "uuid") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."retract_report"("p_report_id" "uuid") IS '将 submitted/rejected 报告撤回为 draft。';



CREATE OR REPLACE FUNCTION "public"."reuse_template"("p_report_type" "text", "p_language" "text", "p_same_as_report_type" "text") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
    AS $$
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


ALTER FUNCTION "public"."reuse_template"("p_report_type" "text", "p_language" "text", "p_same_as_report_type" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."reuse_template"("p_report_type" "text", "p_language" "text", "p_same_as_report_type" "text") IS '让 report_type 的模板记录复用 same_as_report_type 的文件路径（静态复制）。';



CREATE OR REPLACE FUNCTION "public"."set_updated_at_utc"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
begin
  new.updated_at = now();
  return new;
end;
$$;


ALTER FUNCTION "public"."set_updated_at_utc"() OWNER TO "postgres";


COMMENT ON FUNCTION "public"."set_updated_at_utc"() IS '通用 BEFORE UPDATE 触发器函数，将 NEW.updated_at 设为当前 UTC 时间（now()）。被所有含 updated_at 字段的表的 trg_*_updated_at 触发器调用。';



CREATE OR REPLACE FUNCTION "public"."submit_report"("p_report_id" "uuid") RETURNS TABLE("report_id" "uuid", "status" "text")
    LANGUAGE "plpgsql"
    AS $$
declare
    v_current_status text;
begin
    select r.status
      into v_current_status
      from public.report r
     where r.id = p_report_id;

    if not found then
        raise exception '报告不存在: %', p_report_id;
    end if;

    if v_current_status not in ('draft', 'rejected') then
        raise exception '报告状态为 %，无法提交（仅 draft/rejected 可提交）', v_current_status;
    end if;

    perform public.validate_report(p_report_id);

    update public.report
       set status = 'submitted',
           rejection_reason = null
     where id = p_report_id;

    return query select p_report_id, 'submitted'::text;
end;
$$;


ALTER FUNCTION "public"."submit_report"("p_report_id" "uuid") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."submit_report"("p_report_id" "uuid") IS '将 draft/rejected 报告提交为 submitted，提交前校验 report 自身文件路径与字段完整性。';



CREATE OR REPLACE FUNCTION "public"."update_model_path"("p_report_id" "uuid", "p_model_path" "text") RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
begin
    if coalesce(btrim(p_model_path), '') = '' then
        raise exception 'model_path 不能为空';
    end if;

    update public.report
       set model_path = p_model_path
     where id = p_report_id
       and status in ('draft', 'rejected');

    if not found then
        raise exception '报告不存在或当前状态不允许更新模型路径: %', p_report_id;
    end if;
end;
$$;


ALTER FUNCTION "public"."update_model_path"("p_report_id" "uuid", "p_model_path" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."update_model_path"("p_report_id" "uuid", "p_model_path" "text") IS '更新报告当前模型路径，要求 report 处于 draft 或 rejected。';



CREATE OR REPLACE FUNCTION "public"."update_report_doc_paths"("p_report_id" "uuid", "p_word_path" "text", "p_pdf_path" "text") RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
begin
    if coalesce(btrim(p_word_path), '') = '' then
        raise exception 'word_path 不能为空';
    end if;
    if coalesce(btrim(p_pdf_path), '') = '' then
        raise exception 'pdf_path 不能为空';
    end if;

    update public.report
       set word_path = p_word_path,
           pdf_path = p_pdf_path
     where id = p_report_id
       and status in ('draft', 'rejected');

    if not found then
        raise exception '报告不存在或当前状态不允许更新文档路径: %', p_report_id;
    end if;
end;
$$;


ALTER FUNCTION "public"."update_report_doc_paths"("p_report_id" "uuid", "p_word_path" "text", "p_pdf_path" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."update_report_doc_paths"("p_report_id" "uuid", "p_word_path" "text", "p_pdf_path" "text") IS '更新报告当前 Word/PDF 路径，要求 report 处于 draft 或 rejected。';



CREATE OR REPLACE FUNCTION "public"."upsert_report"("p_draft" "jsonb") RETURNS TABLE("report_id" "uuid")
    LANGUAGE "plpgsql"
    AS $$
declare
    v_report_id      uuid;
    v_is_new         boolean;
    v_analyst_emails text[];
    v_lead_analyst   text;
begin
    v_report_id := (p_draft->>'report_id')::uuid;

    if v_report_id is null then
        raise exception 'report_id 不能为空，请在调用前用 uuid.uuid4() 生成';
    end if;

    if p_draft->'analysts' is null or jsonb_array_length(p_draft->'analysts') = 0 then
        raise exception 'analysts 不能为空';
    end if;

    select array_agg(lower(btrim(elem->>'analyst_email')) order by (elem->>'author_order')::integer)
      into v_analyst_emails
      from jsonb_array_elements(p_draft->'analysts') elem;

    v_lead_analyst := v_analyst_emails[1];

    select not exists (
        select 1 from public.report where id = v_report_id
    ) into v_is_new;

    if v_is_new then
        insert into public.report (
            id, title, report_type, status, owner_user_id,
            coverage_id, ticker, sector_id, region_code, rating, target_price,
            investment_thesis, report_language, contact_person,
            lead_analyst_email, analyst_emails
        ) values (
            v_report_id,
            p_draft->>'title',
            p_draft->>'report_type',
            'draft',
            auth.uid(),
            (p_draft->>'coverage_id')::uuid,
            p_draft->>'ticker',
            (p_draft->>'sector_id')::uuid,
            p_draft->>'region_code',
            p_draft->>'rating',
            (p_draft->>'target_price')::numeric,
            p_draft->>'investment_thesis',
            p_draft->>'report_language',
            p_draft->>'contact_person',
            v_lead_analyst,
            v_analyst_emails
        );
    else
        update public.report
           set title              = p_draft->>'title',
               report_type        = p_draft->>'report_type',
               coverage_id        = (p_draft->>'coverage_id')::uuid,
               ticker             = p_draft->>'ticker',
               sector_id          = (p_draft->>'sector_id')::uuid,
               region_code        = p_draft->>'region_code',
               rating             = p_draft->>'rating',
               target_price       = (p_draft->>'target_price')::numeric,
               investment_thesis  = p_draft->>'investment_thesis',
               report_language    = p_draft->>'report_language',
               contact_person     = p_draft->>'contact_person',
               lead_analyst_email = v_lead_analyst,
               analyst_emails     = v_analyst_emails
         where id = v_report_id
           and status in ('draft', 'rejected');

        if not found then
            raise exception '仅 draft/rejected 状态可更新报告元数据';
        end if;
    end if;

    return query select v_report_id;
end;
$$;


ALTER FUNCTION "public"."upsert_report"("p_draft" "jsonb") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."upsert_report"("p_draft" "jsonb") IS '创建或更新 report 元数据，不生成版本号，不操作 Storage 路径。';



CREATE OR REPLACE FUNCTION "public"."upsert_template_record"("p_report_type" "text", "p_language" "text") RETURNS "void"
    LANGUAGE "plpgsql" SECURITY DEFINER
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


ALTER FUNCTION "public"."upsert_template_record"("p_report_type" "text", "p_language" "text") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."upsert_template_record"("p_report_type" "text", "p_language" "text") IS '上传文件后调用，服务端按固定规则生成路径（含 bucket 前缀）并 upsert report_template 记录。';



CREATE OR REPLACE FUNCTION "public"."validate_report"("p_report_id" "uuid") RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
declare
    v_errors      text[] := '{}';
    v_report      record;
    v_bad_analyst record;
begin
    select r.status,
           r.title, r.report_type, r.report_language,
           r.investment_thesis, r.contact_person,
           r.coverage_id, r.sector_id, r.region_code,
           r.analyst_emails,
           r.word_path, r.pdf_path
      into v_report
      from public.report r
     where r.id = p_report_id;

    if not found then
        raise exception '报告不存在: %', p_report_id;
    end if;

    if v_report.status not in ('draft', 'rejected') then
        v_errors := v_errors || format('报告状态为 %s，仅 draft/rejected 可提交', v_report.status);
    end if;

    if coalesce(v_report.title, '') = '' then
        v_errors := v_errors || '缺少必填字段：标题（title）';
    end if;
    if coalesce(v_report.report_type, '') = '' then
        v_errors := v_errors || '缺少必填字段：报告类型（report_type）';
    end if;
    if coalesce(v_report.report_language, '') = '' then
        v_errors := v_errors || '缺少必填字段：报告语言（report_language）';
    end if;
    if coalesce(v_report.investment_thesis, '') = '' then
        v_errors := v_errors || '缺少必填字段：投资论点（investment_thesis）';
    end if;
    if coalesce(v_report.contact_person, '') = '' then
        v_errors := v_errors || '缺少必填字段：联系人（contact_person）';
    end if;
    if coalesce(v_report.word_path, '') = '' then
        v_errors := v_errors || '缺少 Word 文件路径（word_path）';
    end if;
    if coalesce(v_report.pdf_path, '') = '' then
        v_errors := v_errors || '缺少 PDF 文件路径（pdf_path）';
    end if;

    if cardinality(v_report.analyst_emails) = 0 then
        v_errors := v_errors || '报告没有分析师（analyst_emails 为空）';
    else
        if v_report.contact_person is not null
           and not exists (
               select 1
                 from unnest(v_report.analyst_emails) as e
                where lower(e) = lower(v_report.contact_person)
           ) then
            v_errors := v_errors || format('contact_person（%s）不在本报告分析师列表中', v_report.contact_person);
        end if;

        for v_bad_analyst in
            select e as analyst_email, a.is_active
              from unnest(v_report.analyst_emails) as e
              left join public.analyst a on a.email = lower(e)
             where a.email is null or not a.is_active
        loop
            if v_bad_analyst.is_active is null then
                v_errors := v_errors || format('分析师不存在：%s', v_bad_analyst.analyst_email);
            else
                v_errors := v_errors || format('分析师已停用：%s', v_bad_analyst.analyst_email);
            end if;
        end loop;
    end if;

    if v_report.report_type in ('company', 'company_flash') then
        if v_report.coverage_id is null then
            v_errors := v_errors || format('公司类报告（%s）必须关联 coverage_id', v_report.report_type);
        elsif not exists (select 1 from public.coverage where id = v_report.coverage_id) then
            v_errors := v_errors || format('coverage 不存在：%s', v_report.coverage_id);
        end if;
    end if;

    if v_report.sector_id is not null
       and not exists (select 1 from public.sector where id = v_report.sector_id) then
        v_errors := v_errors || format('sector 不存在：%s', v_report.sector_id);
    end if;

    if v_report.region_code is not null
       and not exists (select 1 from public.region where code = v_report.region_code) then
        v_errors := v_errors || format('region 不存在：%s', v_report.region_code);
    end if;

    if array_length(v_errors, 1) > 0 then
        raise exception '校验失败：%', array_to_string(v_errors, '；');
    end if;
end;
$$;


ALTER FUNCTION "public"."validate_report"("p_report_id" "uuid") OWNER TO "postgres";


COMMENT ON FUNCTION "public"."validate_report"("p_report_id" "uuid") IS '全量校验报告字段完整性，文件路径直接从 report.word_path/pdf_path 读取。';



CREATE OR REPLACE FUNCTION "public"."validate_sector_hierarchy"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
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


ALTER FUNCTION "public"."validate_sector_hierarchy"() OWNER TO "postgres";


COMMENT ON FUNCTION "public"."validate_sector_hierarchy"() IS '行业分类层级校验触发器函数（BEFORE INSERT OR UPDATE）。强制执行：1）禁止自引用（parent_id ≠ id）；2）level=1 不允许有 parent_id；3）level=2 的 parent_id 必须指向已存在的 level=1 行；4）最多两级，禁止更深层级。由 trg_sector_hierarchy 触发器绑定到 sector 表。';



CREATE TABLE IF NOT EXISTS "public"."coverage" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "ticker" "text" NOT NULL,
    "english_name" "text" NOT NULL,
    "chinese_name" "text",
    "traditional_chinese" "text",
    "sector_id" "uuid" NOT NULL,
    "isin" "text" NOT NULL,
    "country_of_domicile" "text" NOT NULL,
    "reporting_currency" "text",
    "is_active" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."coverage" OWNER TO "postgres";


COMMENT ON TABLE "public"."coverage" IS '公司覆盖（Coverage）主表。记录研究所跟踪的上市公司/标的，包含股票代码（ticker）、公司名称、ISIN、所属行业等核心信息。一个 coverage 代表一个被研究覆盖的标的。';



COMMENT ON COLUMN "public"."coverage"."id" IS '公司覆盖 UUID 主键。被 coverage_analyst.coverage_id 和 report.coverage_id 引用';



COMMENT ON COLUMN "public"."coverage"."ticker" IS '股票代码/标的代码（唯一），如 "0700.HK"、"600519.SH"';



COMMENT ON COLUMN "public"."coverage"."english_name" IS '公司英文全称，如 "Tencent Holdings Ltd"';



COMMENT ON COLUMN "public"."coverage"."chinese_name" IS '公司中文简称，如 "腾讯控股"';



COMMENT ON COLUMN "public"."coverage"."traditional_chinese" IS '公司繁体中文名称';



COMMENT ON COLUMN "public"."coverage"."sector_id" IS '所属行业 ID，引用 sector.id。表示该标的主要所属的行业分类';



COMMENT ON COLUMN "public"."coverage"."isin" IS '国际证券识别码 ISIN（唯一），如 "KYG875721634"';



COMMENT ON COLUMN "public"."coverage"."country_of_domicile" IS '注册/所在国家或地区，如 "China"、"Hong Kong"';



COMMENT ON COLUMN "public"."coverage"."reporting_currency" IS '财务报告货币，如 "CNY"、"HKD"、"USD"';



COMMENT ON COLUMN "public"."coverage"."is_active" IS '是否活跃覆盖。true=正在跟踪，false=已终止覆盖';



COMMENT ON COLUMN "public"."coverage"."created_at" IS '记录创建时间（UTC）';



COMMENT ON COLUMN "public"."coverage"."updated_at" IS '记录最后更新时间（UTC），由 trg_coverage_updated_at 触发器自动维护';



CREATE TABLE IF NOT EXISTS "public"."coverage_analyst" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "coverage_id" "uuid" NOT NULL,
    "analyst_email" "text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "author_order" integer NOT NULL
);


ALTER TABLE "public"."coverage_analyst" OWNER TO "postgres";


COMMENT ON TABLE "public"."coverage_analyst" IS '覆盖-分析师关联表（多对多）。记录哪些分析师负责跟踪某个公司覆盖（coverage），以及署名排序。每个 coverage 可关联多个分析师，通过 author_order 排序。';



COMMENT ON COLUMN "public"."coverage_analyst"."id" IS '关联记录 UUID 主键';



COMMENT ON COLUMN "public"."coverage_analyst"."coverage_id" IS '关联的公司覆盖 ID，引用 coverage.id（ON DELETE CASCADE，覆盖删除时级联删除关联分析师）';



COMMENT ON COLUMN "public"."coverage_analyst"."analyst_email" IS '分析师邮箱，引用 analyst.email（逻辑外键）。标识负责该覆盖的分析师';



COMMENT ON COLUMN "public"."coverage_analyst"."created_at" IS '记录创建时间（UTC）';



COMMENT ON COLUMN "public"."coverage_analyst"."updated_at" IS '记录最后更新时间（UTC），由 trg_coverage_analyst_updated_at 触发器自动维护';



COMMENT ON COLUMN "public"."coverage_analyst"."author_order" IS '署名排序号，数字越小排名越靠前，用于报告署名顺序展示';



CREATE TABLE IF NOT EXISTS "public"."rating" (
    "name" "text" NOT NULL,
    "code" "text" NOT NULL,
    "rank" integer DEFAULT 1 NOT NULL
);


ALTER TABLE "public"."rating" OWNER TO "postgres";


COMMENT ON TABLE "public"."rating" IS '评级字典表。存储研究报告中给出的投资评级，如"优于大市/中性/弱于大市/未评级"。报告的 report.rating 字段引用此表 report_rating.code。';



COMMENT ON COLUMN "public"."rating"."name" IS '评级的中文显示名称，如"优于大市"、"中性"、"弱于大市"、"未评级"';



COMMENT ON COLUMN "public"."rating"."code" IS '评级的英文编码（唯一），如 OUTPERFORM、NEUTRAL、UNDERPERFORM、NON_RATED。报告 report.rating 字段存储此编码值';



COMMENT ON COLUMN "public"."rating"."rank" IS '排序权重，值越小排名越靠前，用于前端下拉排序展示';



CREATE TABLE IF NOT EXISTS "public"."region" (
    "name_en" "text" NOT NULL,
    "name_cn" "text" NOT NULL,
    "code" "text" NOT NULL,
    "is_active" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."region" OWNER TO "postgres";


COMMENT ON TABLE "public"."region" IS '区域/市场字典表。存储研究所覆盖的亚太及全球市场区域，如中国、香港、日本、台湾、韩国、印度、澳门、美国。分析师和报告通过 region_code 字段关联此表 region.code。';



COMMENT ON COLUMN "public"."region"."name_en" IS '区域英文名称（唯一），如 China、Hong Kong';



COMMENT ON COLUMN "public"."region"."name_cn" IS '区域中文名称（唯一），如 中国、香港';



COMMENT ON COLUMN "public"."region"."code" IS '区域标准编码（唯一），如 CN、HK、JP、TW。分析师 analyst.region_code 和报告 report.region_code 存储此编码值';



COMMENT ON COLUMN "public"."region"."is_active" IS '是否启用。false 表示已停用，不再出现在下拉选项中';



COMMENT ON COLUMN "public"."region"."created_at" IS '记录创建时间（UTC）';



COMMENT ON COLUMN "public"."region"."updated_at" IS '记录最后更新时间（UTC），由 updated_at 触发器自动维护';



CREATE TABLE IF NOT EXISTS "public"."report" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "title" "text" NOT NULL,
    "report_type" "text" NOT NULL,
    "report_language" "text",
    "status" "text" DEFAULT 'draft'::"text" NOT NULL,
    "owner_user_id" "uuid" NOT NULL,
    "lead_analyst_email" "text" NOT NULL,
    "analyst_emails" "text"[] NOT NULL,
    "contact_person" "text",
    "coverage_id" "uuid",
    "ticker" "text",
    "sector_id" "uuid",
    "region_code" "text",
    "rating" "text",
    "target_price" numeric,
    "investment_thesis" "text",
    "word_path" "text",
    "pdf_path" "text",
    "model_path" "text",
    "published_by" "uuid",
    "published_at" timestamp with time zone,
    "rejection_reason" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "report_language_check" CHECK ((("report_language" IS NULL) OR ("report_language" = ANY (ARRAY['zh'::"text", 'en'::"text"])))),
    CONSTRAINT "report_status_check" CHECK (("status" = ANY (ARRAY['draft'::"text", 'submitted'::"text", 'published'::"text", 'rejected'::"text"]))),
    CONSTRAINT "report_target_price_check" CHECK ((("target_price" IS NULL) OR ("target_price" > (0)::numeric)))
);


ALTER TABLE "public"."report" OWNER TO "postgres";


COMMENT ON TABLE "public"."report" IS '研究报告主表。记录每篇研究报告的核心元数据，包括标题、类型、状态、所属覆盖、评级等。状态机控制流转：draft → submitted → published/rejected，rejected → draft。报告不做物理删除。';



COMMENT ON COLUMN "public"."report"."id" IS '报告 UUID 主键。被 report_status_log.report_id 引用';



COMMENT ON COLUMN "public"."report"."title" IS '报告标题';



COMMENT ON COLUMN "public"."report"."report_type" IS '报告类型编码，引用 report_type.report_type，如 company、sector、macro';



COMMENT ON COLUMN "public"."report"."status" IS '报告当前状态（默认 draft）。合法值：draft（草稿）、submitted（已提交待审批）、published（已发布）、rejected（已退回）。CHECK 约束限制只能为这四个值';



COMMENT ON COLUMN "public"."report"."owner_user_id" IS '报告所有者（创建人）的 UUID，引用 auth.users.id。创建后不可转移';



COMMENT ON COLUMN "public"."report"."coverage_id" IS '关联的公司覆盖 ID，引用 coverage.id。表示本报告研究的标的';



COMMENT ON COLUMN "public"."report"."ticker" IS '标的股票代码，冗余自 coverage.ticker 或手动填写';



COMMENT ON COLUMN "public"."report"."sector_id" IS '关联行业 ID，引用 sector.id。表示报告研究的行业';



COMMENT ON COLUMN "public"."report"."region_code" IS '关联区域编码，引用 region.code。表示报告覆盖的市场区域';



COMMENT ON COLUMN "public"."report"."rating" IS '投资评级编码，引用 rating.code。如 OUTPERFORM、NEUTRAL、UNDERPERFORM、NON_RATED';



COMMENT ON COLUMN "public"."report"."target_price" IS '目标价格（numeric）。CHECK 约束要求必须大于 0';



COMMENT ON COLUMN "public"."report"."investment_thesis" IS '投资论点摘要';



COMMENT ON COLUMN "public"."report"."report_language" IS '报告语言，仅允许 zh（中文）或 en（英文）';



COMMENT ON COLUMN "public"."report"."contact_person" IS '联系人邮箱，引用 analyst.email。报告对外的联系分析师';



COMMENT ON COLUMN "public"."report"."published_by" IS '发布操作执行人 UUID，引用 auth.users.id。仅在 submitted → published 状态流转时记录';



COMMENT ON COLUMN "public"."report"."published_at" IS '发布时间。仅在 submitted → published 状态流转时记录';



COMMENT ON COLUMN "public"."report"."created_at" IS '记录创建时间（UTC）';



COMMENT ON COLUMN "public"."report"."updated_at" IS '记录最后更新时间（UTC），由 trg_report_updated_at 触发器自动维护';



COMMENT ON COLUMN "public"."report"."lead_analyst_email" IS '主分析师邮箱，报告署名的第一作者。引用 analyst.email';



COMMENT ON COLUMN "public"."report"."analyst_emails" IS '所有合著分析师邮箱数组，包含 lead_analyst_email 在内。用于 RLS 策略中判断分析师是否关联该报告';



COMMENT ON COLUMN "public"."report"."rejection_reason" IS '退回原因。仅当 status = rejected 时有值，由 sa 在退回操作时填写';



COMMENT ON COLUMN "public"."report"."word_path" IS '当前 Word 文件在 Storage 中的完整路径。上传新 Word 后直接覆盖为最新路径。';



COMMENT ON COLUMN "public"."report"."pdf_path" IS '当前 PDF 文件在 Storage 中的完整路径。上传新 PDF 后直接覆盖为最新路径。';



COMMENT ON COLUMN "public"."report"."model_path" IS '当前 Model 文件在 Storage 中的完整路径。上传新 Model 后直接覆盖为最新路径。';



CREATE TABLE IF NOT EXISTS "public"."report_status_log" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "report_id" "uuid" NOT NULL,
    "from_status" "text" NOT NULL,
    "to_status" "text" NOT NULL,
    "action_by" "uuid" NOT NULL,
    "action_by_name" "text",
    "action_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "reason" "text",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb" NOT NULL,
    CONSTRAINT "report_status_log_reason_required" CHECK ((("to_status" <> 'rejected'::"text") OR (("reason" IS NOT NULL) AND ("btrim"("reason") <> ''::"text"))))
);


ALTER TABLE "public"."report_status_log" OWNER TO "postgres";


COMMENT ON TABLE "public"."report_status_log" IS '报告状态变更审计日志（append-only，禁止 UPDATE/DELETE）。记录每次状态流转的 from/to、操作人、时间、原因和 metadata 快照。用于审批追溯和合规审计。';



COMMENT ON COLUMN "public"."report_status_log"."id" IS '日志记录 UUID 主键';



COMMENT ON COLUMN "public"."report_status_log"."report_id" IS '关联报告 ID，引用 report.id（ON DELETE CASCADE）';



COMMENT ON COLUMN "public"."report_status_log"."from_status" IS '流转前状态，如 draft、submitted、published、rejected';



COMMENT ON COLUMN "public"."report_status_log"."to_status" IS '流转后状态，如 submitted、published、rejected、draft';



COMMENT ON COLUMN "public"."report_status_log"."action_by" IS '执行状态变更的用户 UUID，引用 auth.users.id';



COMMENT ON COLUMN "public"."report_status_log"."action_by_name" IS '执行人姓名，冗余记录方便展示';



COMMENT ON COLUMN "public"."report_status_log"."action_at" IS '操作时间（UTC，默认当前时间）';



COMMENT ON COLUMN "public"."report_status_log"."reason" IS '退回/审批意见。当 to_status = rejected 时 CHECK 约束要求非空且非空白';



COMMENT ON COLUMN "public"."report_status_log"."metadata" IS '状态变更时的快照数据（JSONB），记录报告当前文件路径等上下文信息';



CREATE TABLE IF NOT EXISTS "public"."report_template" (
    "id" "text" NOT NULL,
    "report_type" "text" NOT NULL,
    "language" "text" DEFAULT 'en'::"text" NOT NULL,
    "template_file_path" "text" NOT NULL,
    "schema_file_path" "text",
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "template_language_check" CHECK (("language" = ANY (ARRAY['en'::"text", 'zh'::"text"])))
);


ALTER TABLE "public"."report_template" OWNER TO "postgres";


COMMENT ON TABLE "public"."report_template" IS '报告模板配置表。每种 report_type × language 组合对应一个模板记录，记录模板文件和 schema 文件的存储路径。系统初始化时预置占位模板（template_file_path 为空字符串），Admin 上传真实文件后覆盖。';



COMMENT ON COLUMN "public"."report_template"."id" IS '模板标识（文本主键），通常由 report_type + language 组合生成，如 "company_en"、"sector_zh"';



COMMENT ON COLUMN "public"."report_template"."report_type" IS '所属报告类型编码，引用 report_type.report_type，如 company、sector';



COMMENT ON COLUMN "public"."report_template"."language" IS '模板语言编码，仅允许 en（英文）或 zh（中文）';



COMMENT ON COLUMN "public"."report_template"."template_file_path" IS '模板文件在 Storage 中的存储路径。初始化占位模板为空字符串';



COMMENT ON COLUMN "public"."report_template"."schema_file_path" IS '模板对应的 JSON Schema 文件路径，用于前端表单校验';



COMMENT ON COLUMN "public"."report_template"."created_at" IS '记录创建时间（UTC）';



COMMENT ON COLUMN "public"."report_template"."updated_at" IS '记录最后更新时间（UTC），由 trg_template_updated_at 触发器自动维护';



CREATE TABLE IF NOT EXISTS "public"."report_type" (
    "name" "text" NOT NULL,
    "report_type" "text" NOT NULL,
    "sort" integer DEFAULT 1 NOT NULL,
    "is_active" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."report_type" OWNER TO "postgres";


COMMENT ON TABLE "public"."report_type" IS '报告类型字典表。定义研究报告的分类，如"公司报告"(company)、"行业报告"(sector)、"宏观报告"(macro) 等。每条记录包含中英文名称和排序权重。';



COMMENT ON COLUMN "public"."report_type"."name" IS '报告类型的中文名称（如"公司报告"）';



COMMENT ON COLUMN "public"."report_type"."report_type" IS '报告类型的英文编码（如 company、sector、macro），用于 report.report_type 和 report_template.report_type 的关联';



COMMENT ON COLUMN "public"."report_type"."sort" IS '排序权重，值越小越靠前，用于前端下拉选项排序';



COMMENT ON COLUMN "public"."report_type"."is_active" IS '是否启用。false 表示已停用，不再出现在下拉选项中';



COMMENT ON COLUMN "public"."report_type"."created_at" IS '记录创建时间（UTC）';



COMMENT ON COLUMN "public"."report_type"."updated_at" IS '记录最后更新时间（UTC），由 trg_report_type_updated_at 触发器自动维护';



CREATE TABLE IF NOT EXISTS "public"."sector" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "level" smallint NOT NULL,
    "parent_id" "uuid",
    "name_en" "text" NOT NULL,
    "name_cn" "text",
    "wind_name" "text",
    "is_active" boolean DEFAULT true NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "sector_level_check" CHECK (("level" = ANY (ARRAY[1, 2]))),
    CONSTRAINT "sector_level_parent_check" CHECK (((("level" = 1) AND ("parent_id" IS NULL)) OR (("level" = 2) AND ("parent_id" IS NOT NULL))))
);


ALTER TABLE "public"."sector" OWNER TO "postgres";


COMMENT ON TABLE "public"."sector" IS '行业分类字典表。采用两级树结构：level=1 为一级行业（如"金融"），level=2 为二级行业（如"银行"），通过 parent_id 挂载到一级行业。报告和公司覆盖通过 sector_id 字段引用此表。约束：level=1 必须无父节点，level=2 必须有父节点。';



COMMENT ON COLUMN "public"."sector"."id" IS '行业 UUID 主键。被 coverage.sector_id 和 report.sector_id 引用';



COMMENT ON COLUMN "public"."sector"."level" IS '层级，仅允许 1（一级行业）或 2（二级行业）。CHECK 约束强制 level=1 时 parent_id 必须为 NULL，level=2 时 parent_id 必须非 NULL';



COMMENT ON COLUMN "public"."sector"."parent_id" IS '父级行业 ID（仅 level=2 时有值），引用 sector.id。level=1 的行此字段为 NULL';



COMMENT ON COLUMN "public"."sector"."name_en" IS '行业英文名称';



COMMENT ON COLUMN "public"."sector"."name_cn" IS '行业中文名称';



COMMENT ON COLUMN "public"."sector"."wind_name" IS '万得（Wind）行业分类体系中的对应名称，用于与外部数据源对齐';



COMMENT ON COLUMN "public"."sector"."is_active" IS '是否启用。false 表示已停用，不再出现在下拉选项中';



COMMENT ON COLUMN "public"."sector"."created_at" IS '记录创建时间（UTC）';



COMMENT ON COLUMN "public"."sector"."updated_at" IS '记录最后更新时间（UTC），由 trg_sector_updated_at 触发器自动维护';



ALTER TABLE ONLY "public"."analyst"
    ADD CONSTRAINT "analyst_pkey" PRIMARY KEY ("email");



ALTER TABLE ONLY "public"."coverage_analyst"
    ADD CONSTRAINT "coverage_analyst_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."coverage_analyst"
    ADD CONSTRAINT "coverage_analyst_uniq_pair" UNIQUE ("coverage_id", "analyst_email");



ALTER TABLE ONLY "public"."coverage"
    ADD CONSTRAINT "coverage_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."rating"
    ADD CONSTRAINT "rating_code_key" UNIQUE ("code");



ALTER TABLE ONLY "public"."rating"
    ADD CONSTRAINT "rating_pkey" PRIMARY KEY ("rank");



ALTER TABLE ONLY "public"."region"
    ADD CONSTRAINT "region_name_cn_key" UNIQUE ("name_cn");



ALTER TABLE ONLY "public"."region"
    ADD CONSTRAINT "region_name_en_key" UNIQUE ("name_en");



ALTER TABLE ONLY "public"."region"
    ADD CONSTRAINT "region_pkey" PRIMARY KEY ("code");



ALTER TABLE ONLY "public"."report"
    ADD CONSTRAINT "report_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."report_status_log"
    ADD CONSTRAINT "report_status_log_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."report_template"
    ADD CONSTRAINT "report_template_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."report_type"
    ADD CONSTRAINT "report_type_pkey" PRIMARY KEY ("report_type");



ALTER TABLE ONLY "public"."sector"
    ADD CONSTRAINT "sector_pkey" PRIMARY KEY ("id");



CREATE UNIQUE INDEX "coverage_analyst_uniq_order" ON "public"."coverage_analyst" USING "btree" ("coverage_id", "author_order");



CREATE INDEX "idx_coverage_sector" ON "public"."coverage" USING "btree" ("sector_id");



CREATE INDEX "idx_report_created_at_desc" ON "public"."report" USING "btree" ("created_at" DESC);



CREATE INDEX "idx_report_owner" ON "public"."report" USING "btree" ("owner_user_id");



CREATE INDEX "idx_report_status" ON "public"."report" USING "btree" ("status");



CREATE INDEX "idx_report_status_log_report" ON "public"."report_status_log" USING "btree" ("report_id");



CREATE INDEX "idx_sector_active" ON "public"."sector" USING "btree" ("is_active");



CREATE INDEX "idx_sector_level_parent" ON "public"."sector" USING "btree" ("level", "parent_id");



CREATE INDEX "idx_template_group" ON "public"."report_template" USING "btree" ("report_type", "language");



CREATE UNIQUE INDEX "uidx_coverage_isin_upper" ON "public"."coverage" USING "btree" ("upper"("btrim"("isin")));



CREATE UNIQUE INDEX "uidx_coverage_ticker_lower" ON "public"."coverage" USING "btree" ("lower"("btrim"("ticker")));



CREATE UNIQUE INDEX "uidx_sector_l1_name_en" ON "public"."sector" USING "btree" ("lower"("name_en")) WHERE ("parent_id" IS NULL);



CREATE UNIQUE INDEX "uidx_sector_l2_parent_name_en" ON "public"."sector" USING "btree" ("parent_id", "lower"("name_en")) WHERE ("parent_id" IS NOT NULL);



CREATE OR REPLACE TRIGGER "trg_analyst_updated_at" BEFORE UPDATE ON "public"."analyst" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at_utc"();



CREATE OR REPLACE TRIGGER "trg_coverage_analyst_updated_at" BEFORE UPDATE ON "public"."coverage_analyst" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at_utc"();



CREATE OR REPLACE TRIGGER "trg_coverage_updated_at" BEFORE UPDATE ON "public"."coverage" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at_utc"();



CREATE OR REPLACE TRIGGER "trg_region_updated_at" BEFORE UPDATE ON "public"."region" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at_utc"();



CREATE OR REPLACE TRIGGER "trg_report_status_transition" BEFORE UPDATE ON "public"."report" FOR EACH ROW EXECUTE FUNCTION "public"."report_enforce_status_transition"();



CREATE OR REPLACE TRIGGER "trg_report_type_updated_at" BEFORE UPDATE ON "public"."report_type" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at_utc"();



CREATE OR REPLACE TRIGGER "trg_report_updated_at" BEFORE UPDATE ON "public"."report" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at_utc"();



CREATE OR REPLACE TRIGGER "trg_report_write_status_log" AFTER UPDATE ON "public"."report" FOR EACH ROW EXECUTE FUNCTION "public"."report_write_status_log"();



CREATE OR REPLACE TRIGGER "trg_sector_hierarchy" BEFORE INSERT OR UPDATE ON "public"."sector" FOR EACH ROW EXECUTE FUNCTION "public"."validate_sector_hierarchy"();



CREATE OR REPLACE TRIGGER "trg_sector_updated_at" BEFORE UPDATE ON "public"."sector" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at_utc"();



CREATE OR REPLACE TRIGGER "trg_template_updated_at" BEFORE UPDATE ON "public"."report_template" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at_utc"();



ALTER TABLE ONLY "public"."coverage_analyst"
    ADD CONSTRAINT "coverage_analyst_coverage_id_fkey" FOREIGN KEY ("coverage_id") REFERENCES "public"."coverage"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."report_status_log"
    ADD CONSTRAINT "report_status_log_report_id_fkey" FOREIGN KEY ("report_id") REFERENCES "public"."report"("id") ON DELETE CASCADE;



ALTER TABLE "public"."analyst" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "coverage_analyst_delete" ON "public"."coverage_analyst" FOR DELETE TO "authenticated" USING (("public"."current_app_role"() = 'admin'::"text"));



CREATE POLICY "coverage_analyst_insert" ON "public"."coverage_analyst" FOR INSERT TO "authenticated" WITH CHECK (("public"."current_app_role"() = ANY (ARRAY['admin'::"text", 'sa'::"text", 'analyst'::"text"])));



CREATE POLICY "coverage_analyst_select" ON "public"."coverage_analyst" FOR SELECT TO "authenticated" USING (true);



CREATE POLICY "coverage_analyst_update" ON "public"."coverage_analyst" FOR UPDATE TO "authenticated" USING (("public"."current_app_role"() = 'admin'::"text")) WITH CHECK (("public"."current_app_role"() = 'admin'::"text"));



ALTER TABLE "public"."coverage" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."coverage_analyst" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "coverage_delete" ON "public"."coverage" FOR DELETE TO "authenticated" USING (("public"."current_app_role"() = 'admin'::"text"));



CREATE POLICY "coverage_insert" ON "public"."coverage" FOR INSERT TO "authenticated" WITH CHECK (("public"."current_app_role"() = ANY (ARRAY['admin'::"text", 'sa'::"text", 'analyst'::"text"])));



CREATE POLICY "coverage_select" ON "public"."coverage" FOR SELECT TO "authenticated" USING (true);



CREATE POLICY "coverage_update" ON "public"."coverage" FOR UPDATE TO "authenticated" USING (("public"."current_app_role"() = 'admin'::"text")) WITH CHECK (("public"."current_app_role"() = 'admin'::"text"));



CREATE POLICY "dict_select" ON "public"."analyst" FOR SELECT TO "authenticated" USING (true);



CREATE POLICY "dict_select" ON "public"."rating" FOR SELECT TO "authenticated" USING (true);



CREATE POLICY "dict_select" ON "public"."region" FOR SELECT TO "authenticated" USING (true);



CREATE POLICY "dict_select" ON "public"."report_template" FOR SELECT TO "authenticated" USING (true);



CREATE POLICY "dict_select" ON "public"."report_type" FOR SELECT TO "authenticated" USING (true);



CREATE POLICY "dict_select" ON "public"."sector" FOR SELECT TO "authenticated" USING (true);



CREATE POLICY "dict_write" ON "public"."analyst" TO "authenticated" USING (("public"."current_app_role"() = 'admin'::"text")) WITH CHECK (("public"."current_app_role"() = 'admin'::"text"));



CREATE POLICY "dict_write" ON "public"."rating" TO "authenticated" USING (("public"."current_app_role"() = 'admin'::"text")) WITH CHECK (("public"."current_app_role"() = 'admin'::"text"));



CREATE POLICY "dict_write" ON "public"."region" TO "authenticated" USING (("public"."current_app_role"() = 'admin'::"text")) WITH CHECK (("public"."current_app_role"() = 'admin'::"text"));



CREATE POLICY "dict_write" ON "public"."report_template" TO "authenticated" USING (("public"."current_app_role"() = 'admin'::"text")) WITH CHECK (("public"."current_app_role"() = 'admin'::"text"));



CREATE POLICY "dict_write" ON "public"."report_type" TO "authenticated" USING (("public"."current_app_role"() = 'admin'::"text")) WITH CHECK (("public"."current_app_role"() = 'admin'::"text"));



CREATE POLICY "dict_write" ON "public"."sector" TO "authenticated" USING (("public"."current_app_role"() = 'admin'::"text")) WITH CHECK (("public"."current_app_role"() = 'admin'::"text"));



ALTER TABLE "public"."rating" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."region" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."report" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "report_delete" ON "public"."report" FOR DELETE TO "authenticated" USING (("public"."current_app_role"() = 'admin'::"text"));



CREATE POLICY "report_insert" ON "public"."report" FOR INSERT TO "authenticated" WITH CHECK ((("public"."current_app_role"() = 'admin'::"text") OR (("public"."current_app_role"() = 'analyst'::"text") AND ("owner_user_id" = "auth"."uid"()))));



CREATE POLICY "report_select" ON "public"."report" FOR SELECT TO "authenticated" USING ((("public"."current_app_role"() = 'admin'::"text") OR (("public"."current_app_role"() = 'sa'::"text") AND ("status" = ANY (ARRAY['submitted'::"text", 'published'::"text", 'rejected'::"text"]))) OR (("public"."current_app_role"() = 'analyst'::"text") AND ("owner_user_id" = "auth"."uid"()))));



CREATE POLICY "report_select_published" ON "public"."report" FOR SELECT TO "authenticated" USING ((("public"."current_app_role"() = 'analyst'::"text") AND ("status" = 'published'::"text")));



ALTER TABLE "public"."report_status_log" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."report_template" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."report_type" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "report_update" ON "public"."report" FOR UPDATE TO "authenticated" USING ((("public"."current_app_role"() = 'admin'::"text") OR (("public"."current_app_role"() = 'analyst'::"text") AND ("owner_user_id" = "auth"."uid"()) AND ("status" = ANY (ARRAY['draft'::"text", 'submitted'::"text", 'rejected'::"text"]))))) WITH CHECK ((("public"."current_app_role"() = 'admin'::"text") OR (("public"."current_app_role"() = 'analyst'::"text") AND ("owner_user_id" = "auth"."uid"()) AND ("status" = 'draft'::"text"))));



CREATE POLICY "report_status_log_insert" ON "public"."report_status_log" FOR INSERT TO "authenticated" WITH CHECK ((("public"."current_app_role"() = 'admin'::"text") OR (("public"."current_app_role"() = 'sa'::"text") AND ("from_status" = ANY (ARRAY['submitted'::"text", 'rejected'::"text"]))) OR (("public"."current_app_role"() = 'analyst'::"text") AND ((("from_status" = 'draft'::"text") AND ("to_status" = 'submitted'::"text")) OR (("from_status" = 'submitted'::"text") AND ("to_status" = 'draft'::"text")) OR (("from_status" = 'rejected'::"text") AND ("to_status" = 'draft'::"text"))) AND (EXISTS ( SELECT 1
   FROM "public"."report" "r"
  WHERE (("r"."id" = "report_status_log"."report_id") AND ("r"."owner_user_id" = "auth"."uid"())))))));



CREATE POLICY "report_status_log_select" ON "public"."report_status_log" FOR SELECT TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM "public"."report" "r"
  WHERE (("r"."id" = "report_status_log"."report_id") AND (("public"."current_app_role"() = 'admin'::"text") OR (("public"."current_app_role"() = 'sa'::"text") AND ("r"."status" = ANY (ARRAY['submitted'::"text", 'published'::"text", 'rejected'::"text"]))) OR (("public"."current_app_role"() = 'analyst'::"text") AND ("r"."owner_user_id" = "auth"."uid"())))))));



ALTER TABLE "public"."sector" ENABLE ROW LEVEL SECURITY;


GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";



REVOKE ALL ON FUNCTION "public"."create_coverage"("p_ticker" "text", "p_english_name" "text", "p_sector_id" "uuid", "p_isin" "text", "p_country_of_domicile" "text", "p_analysts" "jsonb", "p_chinese_name" "text", "p_traditional_chinese" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."create_coverage"("p_ticker" "text", "p_english_name" "text", "p_sector_id" "uuid", "p_isin" "text", "p_country_of_domicile" "text", "p_analysts" "jsonb", "p_chinese_name" "text", "p_traditional_chinese" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."create_coverage"("p_ticker" "text", "p_english_name" "text", "p_sector_id" "uuid", "p_isin" "text", "p_country_of_domicile" "text", "p_analysts" "jsonb", "p_chinese_name" "text", "p_traditional_chinese" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."current_app_role"() TO "anon";
GRANT ALL ON FUNCTION "public"."current_app_role"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."current_app_role"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."generate_upload_path"("p_report_id" "uuid", "p_file_category" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."generate_upload_path"("p_report_id" "uuid", "p_file_category" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."generate_upload_path"("p_report_id" "uuid", "p_file_category" "text") TO "service_role";



REVOKE ALL ON FUNCTION "public"."get_template_storage_paths"("p_report_type" "text", "p_language" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."get_template_storage_paths"("p_report_type" "text", "p_language" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_template_storage_paths"("p_report_type" "text", "p_language" "text") TO "service_role";



REVOKE ALL ON FUNCTION "public"."list_coverage_history"("p_ticker" "text", "p_analyst_email" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."list_coverage_history"("p_ticker" "text", "p_analyst_email" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."list_coverage_history"("p_ticker" "text", "p_analyst_email" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."report_enforce_status_transition"() TO "anon";
GRANT ALL ON FUNCTION "public"."report_enforce_status_transition"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."report_enforce_status_transition"() TO "service_role";



GRANT ALL ON FUNCTION "public"."report_status_is_valid"("from_status" "text", "to_status" "text") TO "anon";
GRANT ALL ON FUNCTION "public"."report_status_is_valid"("from_status" "text", "to_status" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."report_status_is_valid"("from_status" "text", "to_status" "text") TO "service_role";



GRANT ALL ON FUNCTION "public"."report_write_status_log"() TO "anon";
GRANT ALL ON FUNCTION "public"."report_write_status_log"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."report_write_status_log"() TO "service_role";



GRANT ALL ON TABLE "public"."analyst" TO "anon";
GRANT ALL ON TABLE "public"."analyst" TO "authenticated";
GRANT ALL ON TABLE "public"."analyst" TO "service_role";



REVOKE ALL ON FUNCTION "public"."resolve_analyst_by_email"("p_email" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."resolve_analyst_by_email"("p_email" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."resolve_analyst_by_email"("p_email" "text") TO "service_role";



REVOKE ALL ON FUNCTION "public"."resolve_coverage"("p_ticker" "text", "p_analyst_email" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."resolve_coverage"("p_ticker" "text", "p_analyst_email" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."resolve_coverage"("p_ticker" "text", "p_analyst_email" "text") TO "service_role";



REVOKE ALL ON FUNCTION "public"."retract_report"("p_report_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."retract_report"("p_report_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."retract_report"("p_report_id" "uuid") TO "service_role";



REVOKE ALL ON FUNCTION "public"."reuse_template"("p_report_type" "text", "p_language" "text", "p_same_as_report_type" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."reuse_template"("p_report_type" "text", "p_language" "text", "p_same_as_report_type" "text") TO "service_role";
GRANT ALL ON FUNCTION "public"."reuse_template"("p_report_type" "text", "p_language" "text", "p_same_as_report_type" "text") TO "authenticated";



GRANT ALL ON FUNCTION "public"."set_updated_at_utc"() TO "anon";
GRANT ALL ON FUNCTION "public"."set_updated_at_utc"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."set_updated_at_utc"() TO "service_role";



REVOKE ALL ON FUNCTION "public"."submit_report"("p_report_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."submit_report"("p_report_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."submit_report"("p_report_id" "uuid") TO "service_role";



REVOKE ALL ON FUNCTION "public"."update_model_path"("p_report_id" "uuid", "p_model_path" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."update_model_path"("p_report_id" "uuid", "p_model_path" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_model_path"("p_report_id" "uuid", "p_model_path" "text") TO "service_role";



REVOKE ALL ON FUNCTION "public"."update_report_doc_paths"("p_report_id" "uuid", "p_word_path" "text", "p_pdf_path" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."update_report_doc_paths"("p_report_id" "uuid", "p_word_path" "text", "p_pdf_path" "text") TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_report_doc_paths"("p_report_id" "uuid", "p_word_path" "text", "p_pdf_path" "text") TO "service_role";



REVOKE ALL ON FUNCTION "public"."upsert_report"("p_draft" "jsonb") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."upsert_report"("p_draft" "jsonb") TO "authenticated";
GRANT ALL ON FUNCTION "public"."upsert_report"("p_draft" "jsonb") TO "service_role";



REVOKE ALL ON FUNCTION "public"."upsert_template_record"("p_report_type" "text", "p_language" "text") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."upsert_template_record"("p_report_type" "text", "p_language" "text") TO "service_role";
GRANT ALL ON FUNCTION "public"."upsert_template_record"("p_report_type" "text", "p_language" "text") TO "authenticated";



REVOKE ALL ON FUNCTION "public"."validate_report"("p_report_id" "uuid") FROM PUBLIC;
GRANT ALL ON FUNCTION "public"."validate_report"("p_report_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."validate_report"("p_report_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."validate_sector_hierarchy"() TO "anon";
GRANT ALL ON FUNCTION "public"."validate_sector_hierarchy"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."validate_sector_hierarchy"() TO "service_role";



GRANT ALL ON TABLE "public"."coverage" TO "anon";
GRANT ALL ON TABLE "public"."coverage" TO "authenticated";
GRANT ALL ON TABLE "public"."coverage" TO "service_role";



GRANT ALL ON TABLE "public"."coverage_analyst" TO "anon";
GRANT ALL ON TABLE "public"."coverage_analyst" TO "authenticated";
GRANT ALL ON TABLE "public"."coverage_analyst" TO "service_role";



GRANT ALL ON TABLE "public"."rating" TO "anon";
GRANT ALL ON TABLE "public"."rating" TO "authenticated";
GRANT ALL ON TABLE "public"."rating" TO "service_role";



GRANT ALL ON TABLE "public"."region" TO "anon";
GRANT ALL ON TABLE "public"."region" TO "authenticated";
GRANT ALL ON TABLE "public"."region" TO "service_role";



GRANT ALL ON TABLE "public"."report" TO "anon";
GRANT ALL ON TABLE "public"."report" TO "authenticated";
GRANT ALL ON TABLE "public"."report" TO "service_role";



GRANT ALL ON TABLE "public"."report_status_log" TO "anon";
GRANT ALL ON TABLE "public"."report_status_log" TO "authenticated";
GRANT ALL ON TABLE "public"."report_status_log" TO "service_role";



GRANT ALL ON TABLE "public"."report_template" TO "anon";
GRANT ALL ON TABLE "public"."report_template" TO "authenticated";
GRANT ALL ON TABLE "public"."report_template" TO "service_role";



GRANT ALL ON TABLE "public"."report_type" TO "anon";
GRANT ALL ON TABLE "public"."report_type" TO "authenticated";
GRANT ALL ON TABLE "public"."report_type" TO "service_role";



GRANT ALL ON TABLE "public"."sector" TO "anon";
GRANT ALL ON TABLE "public"."sector" TO "authenticated";
GRANT ALL ON TABLE "public"."sector" TO "service_role";



ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";

-- ===== 以下为 dump 未捕获的补充项 =====

-- 1. 数据库时区设置（ALTER DATABASE 不在 pg_dump 范围内）
-- supabase db reset 的执行顺序：重建空库 → 运行 migrations → 运行 seed
-- 因此 ALTER DATABASE 在每次 reset 时随迁移文件重新执行，持久生效
ALTER DATABASE postgres SET timezone TO 'Asia/Shanghai';

-- 2. storage bucket policies
-- 最终版本：以 055_storage_policies.sql 为基础，
-- 用 110_retract_permission.sql 中的 reports_insert 和 reports_update 替换对应条目
-- 只保留 CREATE POLICY，无需 DROP POLICY IF EXISTS（squash 首次执行）

-- -------------------------------------------------------------------
-- templates bucket
-- -------------------------------------------------------------------

-- 所有已认证用户可读取模板文件（用于生成报告）
create policy templates_select
on storage.objects
for select
to authenticated
using (bucket_id = 'templates');

-- 仅 admin 可上传/更新/删除模板文件
create policy templates_insert
on storage.objects
for insert
to authenticated
with check (
    bucket_id = 'templates'
    and public.current_app_role() = 'admin'
);

create policy templates_update
on storage.objects
for update
to authenticated
using (
    bucket_id = 'templates'
    and public.current_app_role() = 'admin'
);

create policy templates_delete
on storage.objects
for delete
to authenticated
using (
    bucket_id = 'templates'
    and public.current_app_role() = 'admin'
);

-- -------------------------------------------------------------------
-- reports bucket
-- -------------------------------------------------------------------

-- admin 可读取所有报告文件；analyst 可读取自己的；sa 可读取 submitted/published/rejected
create policy reports_select
on storage.objects
for select
to authenticated
using (
    bucket_id = 'reports'
    and (
        public.current_app_role() = 'admin'
        or exists (
            select 1
            from public.report r
            where
                r.id::text = split_part(name, '/', 1)
                and (
                    (public.current_app_role() = 'analyst' and r.owner_user_id = auth.uid())
                    or (
                        public.current_app_role() = 'sa'
                        and r.status = any(array['submitted', 'published', 'rejected'])
                    )
                )
        )
    )
);

-- admin 可上传所有报告文件；analyst 仅可在 draft 状态下上传（110 收紧版）
create policy reports_insert
on storage.objects
for insert
to authenticated
with check (
    bucket_id = 'reports'
    and (
        public.current_app_role() = 'admin'::text
        or exists (
            select 1
            from public.report r
            where
                r.id::text = split_part(name, '/', 1)
                and public.current_app_role() = 'analyst'::text
                and r.owner_user_id = auth.uid()
                and r.status = 'draft'::text
        )
    )
);

-- admin 可修改所有报告文件；analyst 仅可在 draft 状态下修改（110 收紧版）
create policy reports_update
on storage.objects
for update
to authenticated
using (
    bucket_id = 'reports'
    and (
        public.current_app_role() = 'admin'::text
        or exists (
            select 1
            from public.report r
            where
                r.id::text = split_part(name, '/', 1)
                and public.current_app_role() = 'analyst'::text
                and r.owner_user_id = auth.uid()
                and r.status = 'draft'::text
        )
    )
);

-- 仅 admin 可删除报告文件
create policy reports_delete
on storage.objects
for delete
to authenticated
using (
    bucket_id = 'reports'
    and public.current_app_role() = 'admin'
);

-- ===== 3. 修正函数权限 =====
-- Supabase 通过 ALTER DEFAULT PRIVILEGES 自动为 anon 授予 public schema 下所有函数权限。
-- dump 的 REVOKE ALL ON FUNCTION ... FROM PUBLIC 只撤销 PUBLIC 伪角色的权限，
-- 不撤销直接授予 anon 角色的默认权限。以下先统一收回，再按 baseline 重新授权。

REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM anon;

-- 仅安全辅助函数需要 anon 访问（用于 RLS policy 内部调用）
GRANT ALL ON FUNCTION public.current_app_role() TO anon;
GRANT ALL ON FUNCTION public.report_enforce_status_transition() TO anon;
GRANT ALL ON FUNCTION public.report_status_is_valid(text, text) TO anon;
GRANT ALL ON FUNCTION public.report_write_status_log() TO anon;
GRANT ALL ON FUNCTION public.set_updated_at_utc() TO anon;
GRANT ALL ON FUNCTION public.validate_sector_hierarchy() TO anon;

