-- 20260410000200_090_coverage_history_function.sql
-- 新增：analyst 可读所有 published 报告的 RLS policy
-- 新增：list_coverage_history RPC（INVOKER，无 SECURITY DEFINER）

-- ── RLS: analyst 可读所有 published 报告 ──────────────────────────────────────
create policy report_select_published
on public.report
for select
to authenticated
using (
    (public.current_app_role() = 'analyst'::text)
    and (status = 'published'::text)
);

-- ── RPC: list_coverage_history ───────────────────────────────────────────────
create or replace function public.list_coverage_history(
    p_ticker text,
    p_analyst_email text
)
returns table(
    report_id uuid,
    title text,
    rating text,
    target_price numeric,
    published_at timestamp with time zone
)
language plpgsql stable
as $$
declare
    v_coverage_id uuid;
begin
    select rc.coverage_id
    into v_coverage_id
    from public.resolve_coverage(p_ticker, p_analyst_email) rc;

    return query
    select
        r.id as report_id,
        r.title,
        r.rating,
        r.target_price,
        r.published_at
    from public.report r
    where r.coverage_id = v_coverage_id
      and r.status = 'published'
    order by r.published_at desc nulls last, r.id desc;
end;
$$;

comment on function public.list_coverage_history is
'按 ticker + 1作分析师邮箱定位 coverage，返回已发布历史报告（report_id/title/rating/target_price/published_at）。coverage 存在但无历史时返回空列表。';

revoke execute on function public.list_coverage_history from public, anon;
grant execute on function public.list_coverage_history to authenticated;
