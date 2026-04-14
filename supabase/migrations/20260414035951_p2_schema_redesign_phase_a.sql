-- P2 Phase A: schema redesign
-- 1. report 新增当前文件路径列，删除 current_version_no
alter table public.report
  add column word_path text,
  add column pdf_path text,
  add column model_path text;

alter table public.report
  drop column current_version_no;

comment on column public.report.word_path is '当前 Word 文件在 Storage 中的完整路径。上传新 Word 后直接覆盖为最新路径。';
comment on column public.report.pdf_path is '当前 PDF 文件在 Storage 中的完整路径。上传新 PDF 后直接覆盖为最新路径。';
comment on column public.report.model_path is '当前 Model 文件在 Storage 中的完整路径。上传新 Model 后直接覆盖为最新路径。';

-- 2. report_status_log 去掉 version_no
alter table public.report_status_log
  drop column version_no;

comment on table public.report_status_log is '报告状态变更审计日志（append-only，禁止 UPDATE/DELETE）。记录每次状态流转的 from/to、操作人、时间、原因和 metadata 快照。用于审批追溯和合规审计。';

-- 3. 删除 report_version 及其显式策略
drop policy if exists rv_select on public.report_version;
drop policy if exists rv_insert on public.report_version;
drop table if exists public.report_version;

-- 4. 兼容清理：删除旧函数签名
drop function if exists public.commit_draft_version(uuid, integer, text, text, text, jsonb);
drop function if exists public.init_draft_report(jsonb);
drop function if exists public.submit_report(uuid);
drop function if exists public.retract_report(uuid);
drop function if exists public.validate_report(uuid);
drop function if exists public.generate_upload_path(uuid, text);
drop function if exists public.update_report_doc_paths(uuid, text, text);
drop function if exists public.update_model_path(uuid, text);

-- ============================================================
-- 5. 新 RPC: upsert_report（替代 init_draft_report）
-- ============================================================
create function public.upsert_report(
    p_draft jsonb
)
returns table(report_id uuid)
language plpgsql
as $$
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

comment on function public.upsert_report(jsonb) is
'创建或更新 report 元数据，不生成版本号，不操作 Storage 路径。';

revoke execute on function public.upsert_report(jsonb) from public, anon;
grant execute on function public.upsert_report(jsonb) to authenticated;

-- ============================================================
-- 6. 新 RPC: generate_upload_path
-- ============================================================
create function public.generate_upload_path(
    p_report_id uuid,
    p_file_category text
)
returns text
language plpgsql
as $$
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

comment on function public.generate_upload_path(uuid, text) is
'按 reports/{report_id}/{category}/{timestamp}/ 规则生成上传目录前缀。';

revoke execute on function public.generate_upload_path(uuid, text) from public, anon;
grant execute on function public.generate_upload_path(uuid, text) to authenticated;

-- ============================================================
-- 7. 新 RPC: update_report_doc_paths（替代 commit_draft_version 的文档部分）
-- ============================================================
create function public.update_report_doc_paths(
    p_report_id uuid,
    p_word_path text,
    p_pdf_path text
)
returns void
language plpgsql
as $$
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

comment on function public.update_report_doc_paths(uuid, text, text) is
'更新报告当前 Word/PDF 路径，要求 report 处于 draft 或 rejected。';

revoke execute on function public.update_report_doc_paths(uuid, text, text) from public, anon;
grant execute on function public.update_report_doc_paths(uuid, text, text) to authenticated;

-- ============================================================
-- 8. 新 RPC: update_model_path（替代 commit_draft_version 的模型部分）
-- ============================================================
create function public.update_model_path(
    p_report_id uuid,
    p_model_path text
)
returns void
language plpgsql
as $$
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

comment on function public.update_model_path(uuid, text) is
'更新报告当前模型路径，要求 report 处于 draft 或 rejected。';

revoke execute on function public.update_model_path(uuid, text) from public, anon;
grant execute on function public.update_model_path(uuid, text) to authenticated;

-- ============================================================
-- 9. 重写 validate_report：去掉 report_version 依赖
-- ============================================================
create function public.validate_report(p_report_id uuid)
returns void
language plpgsql
as $$
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

comment on function public.validate_report(uuid) is
'全量校验报告字段完整性，文件路径直接从 report.word_path/pdf_path 读取。';

revoke execute on function public.validate_report(uuid) from public, anon;
grant execute on function public.validate_report(uuid) to authenticated;

-- ============================================================
-- 10. 重写 trigger：直接读 NEW 路径字段，不 JOIN report_version
-- ============================================================
create or replace function public.report_write_status_log()
returns trigger
language plpgsql
as $$
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

-- 重建 trigger（先 drop 旧的）
drop trigger if exists trg_report_write_status_log on public.report;

create trigger trg_report_write_status_log
after update on public.report
for each row
execute function public.report_write_status_log();

-- ============================================================
-- 11. 重写 submit_report：去掉 version_no 依赖
-- ============================================================
create function public.submit_report(
    p_report_id uuid
)
returns table(report_id uuid, status text)
language plpgsql
as $$
declare
    v_current_status text;
begin
    select status
      into v_current_status
      from public.report
     where id = p_report_id;

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

comment on function public.submit_report(uuid) is
'将 draft/rejected 报告提交为 submitted，提交前校验 report 自身文件路径与字段完整性。';

revoke execute on function public.submit_report(uuid) from public, anon;
grant execute on function public.submit_report(uuid) to authenticated;

-- ============================================================
-- 12. 重写 retract_report：去掉 version_no 依赖
-- ============================================================
create function public.retract_report(
    p_report_id uuid
)
returns table(report_id uuid, status text)
language plpgsql
as $$
declare
    v_current_status text;
begin
    select status
      into v_current_status
      from public.report
     where id = p_report_id;

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

comment on function public.retract_report(uuid) is
'将 submitted/rejected 报告撤回为 draft。';

revoke execute on function public.retract_report(uuid) from public, anon;
grant execute on function public.retract_report(uuid) to authenticated;

-- ============================================================
-- Migration 注释
-- ============================================================
comment on function public.report_write_status_log is
'AFTER UPDATE 触发器函数：当 report.status 变化时自动写入 report_status_log，metadata 直接记录 report 当前文件路径。';
