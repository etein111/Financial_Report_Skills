-- 20260413000400_113_submit_report_call_validate.sql
-- submit_report 在状态校验后调用 validate_report，实现字段完整性守门

drop function if exists public.submit_report(uuid);

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
        raise exception '报告状态为 %，无法提交（仅 draft/rejected 可提交）',
            v_current_status;
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

    -- 字段完整性守门：调用 validate_report，校验失败时异常向上传播
    perform public.validate_report(p_report_id);

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
'将 draft/rejected 状态的报告当前版本提交为 submitted。
状态/版本快速失败校验后调用 validate_report 做字段完整性守门，
再原子更新 report.status 并写入 report_status_log。';

revoke execute on function public.submit_report(uuid) from public, anon;
grant execute on function public.submit_report(uuid) to authenticated;
