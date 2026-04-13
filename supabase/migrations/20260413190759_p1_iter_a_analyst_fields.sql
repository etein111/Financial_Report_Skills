-- P1 Iter A: 分析师字段合并
-- 1. report 表新增字段（临时 DEFAULT 通过 NOT NULL 约束）
alter table public.report
  add column lead_analyst_email text not null default '',
  add column analyst_emails    text[] not null default '{}';

-- 2. 移除临时 DEFAULT（防止后续 INSERT 漏传值）
alter table public.report
  alter column lead_analyst_email drop default,
  alter column analyst_emails drop default;

-- 3. 重写 init_draft_report（直接写 lead_analyst_email / analyst_emails）
create or replace function public.init_draft_report(
    p_draft jsonb
)
returns table(report_id uuid, next_version_no integer)
language plpgsql
as $$
declare
    v_report_id      uuid;
    v_next_version   integer;
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

    -- 从 analysts 数组提取排序后的邮箱列表
    select array_agg(lower(btrim(elem->>'analyst_email')) order by (elem->>'author_order')::integer)
      into v_analyst_emails
      from jsonb_array_elements(p_draft->'analysts') elem;

    v_lead_analyst := v_analyst_emails[1];

    select not exists(
        select 1 from public.report where id = v_report_id
    ) into v_is_new;

    if v_is_new then
        v_next_version := 1;

        insert into public.report (
            id, title, report_type, status, current_version_no, owner_user_id,
            coverage_id, ticker, sector_id, region_code, rating, target_price,
            investment_thesis, report_language, contact_person,
            lead_analyst_email, analyst_emails
        ) values (
            v_report_id,
            p_draft->>'title',
            p_draft->>'report_type',
            'draft',
            0,
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
        select r.current_version_no + 1 into v_next_version
        from public.report r
        where r.id = v_report_id;

        update public.report set
            title              = p_draft->>'title',
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
        where id = v_report_id;
    end if;

    return query select v_report_id, v_next_version;
end;
$$;

comment on function public.init_draft_report is
'创建或更新 report 主表字段（含 analyst_emails 内联）。
返回 next_version_no 供 Python 侧上传文件后调用 commit_draft_version。
不写入 report_version，不更新 current_version_no。';

revoke execute on function public.init_draft_report from public, anon;
grant execute on function public.init_draft_report to authenticated;

-- 4. 重写 validate_report（从 report.analyst_emails 读取）
create or replace function public.validate_report(p_report_id uuid)
returns void
language plpgsql
as $$
declare
    v_errors       text[] := '{}';
    v_report       record;
    v_version      record;
    v_bad_analyst  record;
begin
    -- 1. 报告存在（立即 RAISE）
    select r.status, r.current_version_no,
           r.title, r.report_type, r.report_language,
           r.investment_thesis, r.contact_person,
           r.coverage_id, r.sector_id, r.region_code,
           r.analyst_emails
      into v_report
      from public.report r
     where r.id = p_report_id;

    if not found then
        raise exception '报告不存在: %', p_report_id;
    end if;

    -- 2. 状态校验
    if v_report.status not in ('draft', 'rejected') then
        v_errors := v_errors || format(
            '报告状态为 %s，仅 draft/rejected 可提交', v_report.status);
    end if;

    -- 3. 必填字段
    if v_report.title is null or v_report.title = '' then
        v_errors := v_errors || '缺少必填字段：标题（title）';
    end if;
    if v_report.report_type is null or v_report.report_type = '' then
        v_errors := v_errors || '缺少必填字段：报告类型（report_type）';
    end if;
    if v_report.report_language is null or v_report.report_language = '' then
        v_errors := v_errors || '缺少必填字段：报告语言（report_language）';
    end if;
    if v_report.investment_thesis is null or v_report.investment_thesis = '' then
        v_errors := v_errors || '缺少必填字段：投资论点（investment_thesis）';
    end if;
    if v_report.contact_person is null or v_report.contact_person = '' then
        v_errors := v_errors || '缺少必填字段：联系人（contact_person）';
    end if;

    -- 4. 版本存在性
    if coalesce(v_report.current_version_no, 0) <= 0 then
        v_errors := v_errors || '报告当前没有可校验版本';
    else
        select rv.word_file_path, rv.pdf_file_path
          into v_version
          from public.report_version rv
         where rv.report_id = p_report_id
           and rv.version_no = v_report.current_version_no;

        if not found then
            v_errors := v_errors || format('当前版本 v%s 不存在', v_report.current_version_no);
        else
            -- 5. 文件路径
            if v_version.word_file_path is null or v_version.word_file_path = '' then
                v_errors := v_errors || '缺少 Word 文件路径（word_file_path）';
            end if;
            if v_version.pdf_file_path is null or v_version.pdf_file_path = '' then
                v_errors := v_errors || '缺少 PDF 文件路径（pdf_file_path）';
            end if;
        end if;
    end if;

    -- 6. 分析师列表非空（从 report.analyst_emails 数组读取）
    if cardinality(v_report.analyst_emails) = 0 then
        v_errors := v_errors || '报告没有分析师（analyst_emails 为空）';
    else
        -- contact_person 在分析师列表中（大小写不敏感）
        if v_report.contact_person is not null
           and not exists (
               select 1
                 from unnest(v_report.analyst_emails) as e
                where lower(e) = lower(v_report.contact_person)
           ) then
            v_errors := v_errors || format(
                'contact_person（%s）不在本报告分析师列表中', v_report.contact_person);
        end if;

        -- 收集所有问题分析师（不存在或已停用）
        for v_bad_analyst in
            select e as analyst_email,
                   a.is_active
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

    -- 7. company / company_flash：coverage_id 必填且存在
    if v_report.report_type in ('company', 'company_flash') then
        if v_report.coverage_id is null then
            v_errors := v_errors || format(
                '公司类报告（%s）必须关联 coverage_id', v_report.report_type);
        elsif not exists (
            select 1 from public.coverage where id = v_report.coverage_id
        ) then
            v_errors := v_errors || format('coverage 不存在：%s', v_report.coverage_id);
        end if;
    end if;

    -- 8. sector_id 有值时验证存在性
    if v_report.sector_id is not null
       and not exists (select 1 from public.sector where id = v_report.sector_id) then
        v_errors := v_errors || format('sector 不存在：%s', v_report.sector_id);
    end if;

    -- 9. region_code 有值时验证存在性
    if v_report.region_code is not null
       and not exists (select 1 from public.region where code = v_report.region_code) then
        v_errors := v_errors || format('region 不存在：%s', v_report.region_code);
    end if;

    -- 全部错误一次抛出
    if array_length(v_errors, 1) > 0 then
        raise exception '校验失败：%', array_to_string(v_errors, '；');
    end if;
end;
$$;

comment on function public.validate_report(uuid) is
'全量校验报告字段完整性。分析师校验从 report.analyst_emails 数组读取，不再查 report_analyst 表。';

revoke execute on function public.validate_report(uuid) from public, anon;
grant execute on function public.validate_report(uuid) to authenticated;

-- 5. 删除 report_analyst 表依赖（RLS policy、触发器）
drop policy if exists ra_select on public.report_analyst;
drop policy if exists ra_insert on public.report_analyst;
drop policy if exists ra_delete on public.report_analyst;
drop trigger if exists trg_report_analyst_updated_at on public.report_analyst;

-- 6. 删除 report_analyst 表
drop table if exists public.report_analyst;
