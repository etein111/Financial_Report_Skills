-- 20260413000500_114_validate_report_all_analysts.sql
-- 修复：validate_report 分析师校验从只报告第一个改为收集全部

create or replace function public.validate_report(p_report_id uuid)
returns void
language plpgsql
as $$
declare
    v_errors         text[] := '{}';
    v_report         record;
    v_version        record;
    v_analyst_count  integer;
    v_bad_analyst    record;
begin
    -- 1. 报告存在（立即 RAISE，不入数组）
    select r.status, r.current_version_no,
           r.title, r.report_type, r.report_language,
           r.investment_thesis, r.contact_person,
           r.coverage_id, r.sector_id, r.region_code
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

    -- 6. 分析师列表非空
    select count(*)
      into v_analyst_count
      from public.report_analyst
     where report_id = p_report_id;

    if v_analyst_count = 0 then
        v_errors := v_errors || '报告没有分析师（report_analyst 为空）';
    else
        -- contact_person 在分析师列表中（大小写不敏感）
        if v_report.contact_person is not null
           and not exists (
               select 1
                 from public.report_analyst
                where report_id = p_report_id
                  and lower(analyst_email) = lower(v_report.contact_person)
           ) then
            v_errors := v_errors || format(
                'contact_person（%s）不在本报告分析师列表中', v_report.contact_person);
        end if;

        -- 收集所有问题分析师（不存在或已停用），逐个报告
        for v_bad_analyst in
            select ra.analyst_email,
                   a.is_active
              from public.report_analyst ra
              left join public.analyst a on a.email = ra.analyst_email
             where ra.report_id = p_report_id
               and (a.email is null or not a.is_active)
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
