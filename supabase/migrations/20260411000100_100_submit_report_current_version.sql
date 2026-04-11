-- 20260411000100_100_submit_report_current_version.sql
-- submit_report 改为只接收 report_id，并在数据库侧读取 current_version_no

drop function if exists public.submit_report(uuid, integer);

create or replace function public.submit_report(
    p_report_id uuid
)
returns table(report_id uuid, version_no integer, status text)
language plpgsql
as $$
declare
    v_current_status     text;
    v_current_version_no integer;
    v_action_email       text;
begin
    select r.status, r.current_version_no
      into v_current_status, v_current_version_no
    from public.report r
    where r.id = p_report_id;

    if not found then
        raise exception '报告不存在: %', p_report_id;
    end if;

    if v_current_status not in ('draft', 'rejected') then
        raise exception '报告状态为 %，无法提交（仅 draft/rejected 可提交）', v_current_status;
    end if;

    if coalesce(v_current_version_no, 0) <= 0 then
        raise exception '报告当前没有可提交版本';
    end if;

    if not exists (
        select 1
        from public.report_version rv
        where rv.report_id = p_report_id
          and rv.version_no = v_current_version_no
    ) then
        raise exception '当前版本 v% 不存在', v_current_version_no;
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
        auth.uid(), v_action_email, v_current_version_no
    );

    return query
        select p_report_id, v_current_version_no, 'submitted'::text;
end;
$$;

comment on function public.submit_report(uuid) is
'将 draft/rejected 状态的报告当前版本提交为 submitted。数据库侧读取 report.current_version_no，
拒绝 current_version_no<=0 或当前版本缺失的报告，并将真实版本号写入 report_status_log。';

revoke execute on function public.submit_report(uuid) from public, anon;
grant execute on function public.submit_report(uuid) to authenticated;
