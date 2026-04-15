-- 1. 删除 resolve_analyst_by_email（已改为 Python 直接查表）
DROP FUNCTION IF EXISTS public.resolve_analyst_by_email(text);

-- 2. 修改 report_update RLS policy，追加 SA 权限
DROP POLICY IF EXISTS report_update ON public.report;

CREATE POLICY report_update ON public.report
FOR UPDATE TO authenticated
USING (
    (public.current_app_role() = 'admin')
    OR (public.current_app_role() = 'analyst'
        AND owner_user_id = auth.uid()
        AND status = ANY (ARRAY['draft', 'submitted', 'rejected']))
    OR (public.current_app_role() = 'sa'
        AND status = 'submitted')
)
WITH CHECK (
    (public.current_app_role() = 'admin')
    OR (public.current_app_role() = 'analyst'
        AND owner_user_id = auth.uid()
        AND status = 'draft')
    OR (public.current_app_role() = 'sa'
        AND status IN ('published', 'rejected'))
);

-- 3. publish_report：submitted → published
CREATE OR REPLACE FUNCTION public.publish_report(p_report_id uuid)
RETURNS TABLE(report_id uuid, status text)
LANGUAGE plpgsql
AS $$
declare
    v_status text;
begin
    select status into v_status
      from public.report
     where id = p_report_id;

    if not found then
        raise exception '报告不存在: %', p_report_id;
    end if;

    if v_status <> 'submitted' then
        raise exception '报告状态为 %，无法发布（仅 submitted 可发布）', v_status;
    end if;

    update public.report
       set status = 'published',
           published_by = auth.uid(),
           published_at = now()
     where id = p_report_id;

    return query select p_report_id, 'published'::text;
end;
$$;

COMMENT ON FUNCTION public.publish_report(uuid) IS '将 submitted 报告发布为 published，记录 published_by 和 published_at。';

-- 4. reject_report：submitted → rejected
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

    select status into v_status
      from public.report
     where id = p_report_id;

    if not found then
        raise exception '报告不存在: %', p_report_id;
    end if;

    if v_status <> 'submitted' then
        raise exception '报告状态为 %，无法退回（仅 submitted 可退回）', v_status;
    end if;

    update public.report
       set status = 'rejected',
           rejection_reason = p_rejection_reason
     where id = p_report_id;

    return query select p_report_id, 'rejected'::text;
end;
$$;

COMMENT ON FUNCTION public.reject_report(uuid, text) IS '将 submitted 报告退回为 rejected，必填退回原因。';

-- 5. 权限授予
REVOKE ALL ON FUNCTION public.publish_report(uuid) FROM PUBLIC;
GRANT ALL ON FUNCTION public.publish_report(uuid) TO authenticated;
GRANT ALL ON FUNCTION public.publish_report(uuid) TO service_role;

REVOKE ALL ON FUNCTION public.reject_report(uuid, text) FROM PUBLIC;
GRANT ALL ON FUNCTION public.reject_report(uuid, text) TO authenticated;
GRANT ALL ON FUNCTION public.reject_report(uuid, text) TO service_role;
