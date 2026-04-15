-- 修复 publish_report / reject_report 中 status 列引用歧义
-- RETURNS TABLE(report_id, status) 的 status 与 report.status 冲突
-- 解决方式：与 submit_report / retract_report 一致，使用表别名消歧

CREATE OR REPLACE FUNCTION public.publish_report(p_report_id uuid)
RETURNS TABLE(report_id uuid, status text)
LANGUAGE plpgsql
AS $$
declare
    v_status text;
begin
    select r.status into v_status
      from public.report r
     where r.id = p_report_id;

    if not found then
        raise exception '报告不存在: %', p_report_id;
    end if;

    if v_status <> 'submitted' then
        raise exception '报告状态为 %，无法发布（仅 submitted 可发布）', v_status;
    end if;

    update public.report r
       set r.status = 'published',
           r.published_by = auth.uid(),
           r.published_at = now()
     where r.id = p_report_id;

    return query select p_report_id, 'published'::text;
end;
$$;

COMMENT ON FUNCTION public.publish_report(uuid) IS '将 submitted 报告发布为 published，记录 published_by 和 published_at。';

CREATE OR REPLACE FUNCTION public.reject_report(
    p_report_id uuid,
    p_rejection_reason text
)
RETURNS TABLE(report_id uuid, status text)
LANGUAGE plpgsql
AS $$
declare
    v_status text;
begin
    if coalesce(btrim(p_rejection_reason), '') = '' then
        raise exception '退回原因不能为空';
    end if;

    select r.status into v_status
      from public.report r
     where r.id = p_report_id;

    if not found then
        raise exception '报告不存在: %', p_report_id;
    end if;

    if v_status <> 'submitted' then
        raise exception '报告状态为 %，无法退回（仅 submitted 可退回）', v_status;
    end if;

    update public.report r
       set r.status = 'rejected',
           r.rejection_reason = p_rejection_reason
     where r.id = p_report_id;

    return query select p_report_id, 'rejected'::text;
end;
$$;

COMMENT ON FUNCTION public.reject_report(uuid, text) IS '将 submitted 报告退回为 rejected，必填退回原因。';
