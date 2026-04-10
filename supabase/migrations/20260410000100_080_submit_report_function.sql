-- 20260410000100_080_submit_report_function.sql
-- 1. 扩展 report_status_is_valid：加 rejected → submitted
-- 2. 更新 report_update policy：using 子句加 rejected
-- 3. 更新 rsl_insert policy：analyst 可从 rejected 提交
-- 4. submit_report RPC：draft/rejected → submitted，写入状态日志

-- ----------------------------------------------------------------
-- 1. 扩展状态流转合法性函数（加 rejected → submitted）
-- ----------------------------------------------------------------

create or replace function public.report_status_is_valid(from_status text, to_status text)
returns boolean
language sql
immutable
as $$
    select (from_status = 'draft' and to_status = 'submitted')
        or (from_status = 'submitted' and to_status in ('published', 'rejected'))
        or (from_status = 'rejected' and to_status in ('draft', 'submitted'))
$$;

comment on function public.report_status_is_valid(text, text) is
'判断报告状态流转是否合法（IMMUTABLE）。合法路径：draft→submitted、submitted→published、submitted→rejected、rejected→draft、rejected→submitted。';

-- ----------------------------------------------------------------
-- 2. 更新 report_update policy（using 子句加 rejected，允许 analyst 更新 rejected 报告）
-- ----------------------------------------------------------------

drop policy if exists report_update on public.report;

create policy report_update
on public.report
for update
to authenticated
using (
    (public.current_app_role() = 'admin'::text)
    or (
        (public.current_app_role() = 'analyst'::text)
        and (owner_user_id = auth.uid())
        and (status = any (array['draft'::text, 'submitted'::text, 'rejected'::text]))
    )
)
with check (
    (public.current_app_role() = 'admin'::text)
    or (
        (public.current_app_role() = 'analyst'::text)
        and (owner_user_id = auth.uid())
        and (status = any (array['draft'::text, 'submitted'::text, 'rejected'::text]))
    )
);

-- ----------------------------------------------------------------
-- 3. 更新 rsl_insert policy（analyst 可从 rejected 提交）
-- ----------------------------------------------------------------

drop policy if exists rsl_insert on public.report_status_log;

create policy rsl_insert
on public.report_status_log
for insert
to authenticated
with check (
    (public.current_app_role() = 'admin'::text)
    or (
        (public.current_app_role() = 'sa'::text)
        and (from_status = any (array['submitted'::text, 'rejected'::text]))
    )
    or (
        (public.current_app_role() = 'analyst'::text)
        and (from_status = any (array['draft'::text, 'rejected'::text]))
        and (to_status = 'submitted'::text)
        and exists (
            select 1 from public.report r
            where r.id = report_status_log.report_id
              and r.owner_user_id = auth.uid()
        )
    )
);

-- ----------------------------------------------------------------
-- 4. submit_report RPC：draft/rejected → submitted，写入状态日志
-- ----------------------------------------------------------------

create or replace function public.submit_report(
    p_report_id  uuid,
    p_version_no integer
)
returns table(report_id uuid, version_no integer, status text)
language plpgsql
as $$
declare
    v_current_status text;
    v_action_email   text;
begin
    select r.status into v_current_status
    from public.report r
    where r.id = p_report_id;

    if not found then
        raise exception '报告不存在: %', p_report_id;
    end if;

    if v_current_status not in ('draft', 'rejected') then
        raise exception '报告状态为 %，无法提交（仅 draft/rejected 可提交）', v_current_status;
    end if;

    v_action_email := auth.jwt() ->> 'email';

    update public.report
    set status = 'submitted'
    where id = p_report_id;

    insert into public.report_status_log (
        report_id, from_status, to_status,
        action_by, action_by_name, version_no
    ) values (
        p_report_id, v_current_status, 'submitted',
        auth.uid(), v_action_email, p_version_no
    );

    return query select p_report_id, p_version_no, 'submitted'::text;
end;
$$;

comment on function public.submit_report is
'将 draft/rejected 状态的报告提交为 submitted。原子更新 report.status 并写入 report_status_log。
action_by_name 填调用者邮箱（auth.jwt() ->> email）。Python 侧在调用前须先通过 validate_draft。';

revoke execute on function public.submit_report from public, anon;
grant execute on function public.submit_report to authenticated;
