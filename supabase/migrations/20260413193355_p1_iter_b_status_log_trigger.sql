-- P1 Iter B: 状态日志 metadata + 触发器
-- 1. report 表新增 rejection_reason
alter table public.report
  add column rejection_reason text;

-- 2. report_status_log 表新增 metadata
alter table public.report_status_log
  add column metadata jsonb not null default '{}';

-- 3. AFTER UPDATE 触发器：状态变更时自动写日志 + metadata
create or replace function public.report_write_status_log()
returns trigger
language plpgsql
as $$
declare
    v_version  record;
    v_metadata jsonb;
begin
    if new.status is distinct from old.status then
        -- 读取当前版本文件路径
        select rv.word_file_path, rv.pdf_file_path, rv.model_file_path
          into v_version
          from public.report_version rv
         where rv.report_id = new.id
           and rv.version_no = new.current_version_no;

        -- 构建业务快照
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
            'word_path',          v_version.word_file_path,
            'pdf_path',           v_version.pdf_file_path,
            'model_path',         v_version.model_file_path
        );

        insert into public.report_status_log (
            report_id, from_status, to_status,
            action_by, action_by_name, version_no,
            reason, metadata
        ) values (
            new.id, old.status, new.status,
            auth.uid(), auth.jwt()->>'email',
            new.current_version_no,
            case when new.status = 'rejected' then new.rejection_reason else null end,
            v_metadata
        );
    end if;

    return null;
end;
$$;

comment on function public.report_write_status_log is
'AFTER UPDATE 触发器函数：当 report.status 变化时自动写入 report_status_log + metadata 快照。
不声明 SECURITY DEFINER，以调用者身份执行，依赖 rsl_insert RLS policy。';

create trigger trg_report_write_status_log
after update on public.report
for each row
execute function public.report_write_status_log();

-- 4. 重写 submit_report（触发器接管日志 + 清除 rejection_reason）
create or replace function public.submit_report(
    p_report_id uuid
)
returns table(report_id uuid, version_no integer, status text)
language plpgsql
as $$
declare
    v_current_status     text;
    v_current_version_no integer;
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

    -- 字段完整性守门
    perform public.validate_report(p_report_id);

    -- 更新状态并清除 rejection_reason（触发器自动写日志）
    update public.report
       set status = 'submitted', rejection_reason = null
     where id = p_report_id;

    return query
        select p_report_id, v_current_version_no, 'submitted'::text;
end;
$$;

comment on function public.submit_report is
'将 draft/rejected 报告当前版本提交为 submitted。触发器自动写入 report_status_log。';

revoke execute on function public.submit_report(uuid) from public, anon;
grant execute on function public.submit_report(uuid) to authenticated;

-- 5. 重写 retract_report（触发器接管日志 + 清除 rejection_reason）
create or replace function public.retract_report(
    p_report_id uuid
)
returns table(report_id uuid, version_no integer, status text)
language plpgsql
as $$
declare
    v_current_status     text;
    v_current_version_no integer;
begin
    select r.status, r.current_version_no
      into v_current_status, v_current_version_no
      from public.report r
     where r.id = p_report_id;

    if not found then
        raise exception '报告不存在: %', p_report_id;
    end if;

    if v_current_status not in ('submitted', 'rejected') then
        raise exception '报告状态为 %，无法撤回（仅 submitted/rejected 可撤回）', v_current_status;
    end if;

    -- 更新状态并清除 rejection_reason（触发器自动写日志）
    update public.report
       set status = 'draft', rejection_reason = null
     where id = p_report_id;

    return query
        select p_report_id, v_current_version_no, 'draft'::text;
end;
$$;

comment on function public.retract_report is
'将 submitted/rejected 报告撤回为 draft。触发器自动写入 report_status_log。';

revoke execute on function public.retract_report(uuid) from public, anon;
grant execute on function public.retract_report(uuid) to authenticated;
