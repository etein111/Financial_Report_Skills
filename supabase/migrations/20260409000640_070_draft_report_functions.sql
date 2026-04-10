-- 20260409000640_070_draft_report_functions.sql
-- ra_delete policy + init_draft_report + commit_draft_version RPC

-- ----------------------------------------------------------------
-- ra_delete policy：analyst 可删除自己报告的 report_analyst 记录
-- ----------------------------------------------------------------

create policy ra_delete
on public.report_analyst
for delete
to authenticated
using (
    public.current_app_role() = 'admin'
    or (
        public.current_app_role() = 'analyst'
        and exists (
            select 1 from public.report r
            where r.id = report_analyst.report_id
              and r.owner_user_id = auth.uid()
        )
    )
);

-- ----------------------------------------------------------------
-- init_draft_report：创建/更新 report + 全量替换 report_analyst
-- 返回 report_id 和 next_version_no，供 Python 侧上传文件后调用 commit_draft_version
-- ----------------------------------------------------------------

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
    v_analyst        jsonb;
begin
    v_report_id := (p_draft->>'report_id')::uuid;

    if v_report_id is null then
        raise exception 'report_id 不能为空，请在调用前用 uuid.uuid4() 生成';
    end if;

    if p_draft->'analysts' is null or jsonb_array_length(p_draft->'analysts') = 0 then
        raise exception 'analysts 不能为空';
    end if;

    select not exists(
        select 1 from public.report where id = v_report_id
    ) into v_is_new;

    if v_is_new then
        v_next_version := 1;

        insert into public.report (
            id, title, report_type, status, current_version_no, owner_user_id,
            coverage_id, ticker, sector_id, region_code, rating, target_price,
            investment_thesis, report_language, contact_person
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
            p_draft->>'contact_person'
        );
    else
        select r.current_version_no + 1 into v_next_version
        from public.report r
        where r.id = v_report_id;

        update public.report set
            title             = p_draft->>'title',
            report_type       = p_draft->>'report_type',
            coverage_id       = (p_draft->>'coverage_id')::uuid,
            ticker            = p_draft->>'ticker',
            sector_id         = (p_draft->>'sector_id')::uuid,
            region_code       = p_draft->>'region_code',
            rating            = p_draft->>'rating',
            target_price      = (p_draft->>'target_price')::numeric,
            investment_thesis = p_draft->>'investment_thesis',
            report_language   = p_draft->>'report_language',
            contact_person    = p_draft->>'contact_person'
        where id = v_report_id;
    end if;

    -- 全量替换 report_analyst
    delete from public.report_analyst ra where ra.report_id = v_report_id;

    for v_analyst in select * from jsonb_array_elements(p_draft->'analysts')
    loop
        insert into public.report_analyst (report_id, analyst_email, author_order)
        values (
            v_report_id,
            lower(btrim(v_analyst->>'analyst_email')),
            (v_analyst->>'author_order')::integer
        );
    end loop;

    return query select v_report_id, v_next_version;
end;
$$;

comment on function public.init_draft_report is
'第一步：创建或更新 report 主表字段，全量替换 report_analyst。
返回 next_version_no 供 Python 侧上传文件到正确路径后调用 commit_draft_version。
不写入 report_version，不更新 current_version_no。';

revoke execute on function public.init_draft_report from public, anon;
grant execute on function public.init_draft_report to authenticated;

-- ----------------------------------------------------------------
-- commit_draft_version：插入 report_version + 更新 current_version_no
-- 在 Python 上传完文件后调用
-- ----------------------------------------------------------------

create or replace function public.commit_draft_version(
    p_report_id     uuid,
    p_version_no    integer,
    p_word_path     text,
    p_pdf_path      text,
    p_model_path    text,
    p_snapshot      jsonb
)
returns table(report_id uuid, version_no integer, status text)
language plpgsql
as $$
begin
    insert into public.report_version (
        report_id, version_no, snapshot_json,
        word_file_path, pdf_file_path, model_file_path, created_by
    ) values (
        p_report_id, p_version_no, p_snapshot,
        p_word_path, p_pdf_path, p_model_path,
        auth.uid()
    );

    update public.report set
        current_version_no = p_version_no
    where id = p_report_id;

    return query
        select p_report_id, p_version_no, 'draft'::text;
end;
$$;

comment on function public.commit_draft_version is
'第二步：文件上传完成后调用。插入 report_version 快照，更新 report.current_version_no。';

revoke execute on function public.commit_draft_version from public, anon;
grant execute on function public.commit_draft_version to authenticated;
