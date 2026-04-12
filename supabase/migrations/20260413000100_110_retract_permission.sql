-- 20260413000100_110_retract_permission.sql
-- P0: 收紧 submitted 权限 + 增加 submitted/rejected → draft 撤回路径
--
-- 变更清单：
--   1. report_status_is_valid：新增 submitted → draft 路径
--   2. report_update RLS：非对称策略（USING 允许 draft/submitted/rejected，
--      WITH CHECK 限制 draft only）
--   3. rv_insert RLS：analyst 仅 draft 可插入版本
--   4. reports bucket INSERT/UPDATE RLS：analyst 仅 draft 可上传/修改文件
--   5. rsl_insert RLS：analyst 增加 submitted→draft、rejected→draft
--   6. 新增 retract_report RPC

-- ===================================================================
-- 1. report_status_is_valid：新增 submitted → draft (retract) 路径
-- ===================================================================

create or replace function public.report_status_is_valid(from_status text, to_status text)
returns boolean
language sql
immutable
as $$
    select (from_status = 'draft' and to_status = 'submitted')
        or (from_status = 'submitted' and to_status in ('published', 'rejected', 'draft'))
        or (from_status = 'rejected' and to_status in ('draft', 'submitted'))
$$;

comment on function public.report_status_is_valid(text, text) is
'判断报告状态流转是否合法（IMMUTABLE）。

合法路径：
  draft → submitted          （analyst 提交审阅）
  submitted → published      （sa 发布）
  submitted → rejected       （sa 退回）
  submitted → draft          （analyst 撤回，由 retract_report RPC 调用）
  rejected → draft           （analyst 撤回，由 retract_report RPC 调用）
  rejected → submitted       （analyst 重新提交）

所有其他路径均为非法，report_enforce_status_transition 触发器会在
UPDATE report 时调用本函数进行校验，非法流转将抛出异常。';

-- ===================================================================
-- 2. report_update RLS：非对称策略
--    USING:   analyst 可见 draft / submitted / rejected 行
--             → retract_report RPC 需要找到 submitted/rejected 行才能更新
--    WITH CHECK: analyst 更新后状态必须为 draft
--             → analyst 无法在保持 submitted 状态下修改任何字段
--             → analyst 无法通过直接 UPDATE 提交报告（必须走 submit_report RPC）
-- ===================================================================

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
        and (status = 'draft'::text)
    )
);

-- ===================================================================
-- 3. rv_insert RLS：analyst 仅可在 draft 状态下插入 report_version
--    收紧前：draft / submitted 均可插入
--    收紧后：仅 draft 可插入
-- ===================================================================

drop policy if exists rv_insert on public.report_version;

create policy rv_insert
on public.report_version
for insert
to authenticated
with check (
    exists (
        select 1
        from public.report r
        where r.id = report_version.report_id
          and (
              (public.current_app_role() = 'admin'::text)
              or (
                  (public.current_app_role() = 'analyst'::text)
                  and (r.owner_user_id = auth.uid())
                  and (r.status = 'draft'::text)
              )
          )
    )
);

-- ===================================================================
-- 4. reports bucket INSERT/UPDATE RLS：analyst 仅可在 draft 状态下上传/修改文件
--    收紧前：draft / submitted 均可上传
--    收紧后：仅 draft 可上传
-- ===================================================================

drop policy if exists reports_insert on storage.objects;

create policy reports_insert
on storage.objects
for insert
to authenticated
with check (
    bucket_id = 'reports'
    and (
        public.current_app_role() = 'admin'::text
        or exists (
            select 1
            from public.report r
            where
                r.id::text = split_part(name, '/', 1)
                and public.current_app_role() = 'analyst'::text
                and r.owner_user_id = auth.uid()
                and r.status = 'draft'::text
        )
    )
);

drop policy if exists reports_update on storage.objects;

create policy reports_update
on storage.objects
for update
to authenticated
using (
    bucket_id = 'reports'
    and (
        public.current_app_role() = 'admin'::text
        or exists (
            select 1
            from public.report r
            where
                r.id::text = split_part(name, '/', 1)
                and public.current_app_role() = 'analyst'::text
                and r.owner_user_id = auth.uid()
                and r.status = 'draft'::text
        )
    )
);

-- ===================================================================
-- 5. rsl_insert RLS：analyst 增加 submitted→draft、rejected→draft
--    收紧前：analyst 仅 draft→submitted
--    收紧后：analyst 可 draft→submitted / submitted→draft / rejected→draft
-- ===================================================================

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
        and (
            (from_status = 'draft'::text and to_status = 'submitted'::text)
            or (from_status = 'submitted'::text and to_status = 'draft'::text)
            or (from_status = 'rejected'::text and to_status = 'draft'::text)
        )
        and exists (
            select 1
            from public.report r
            where r.id = report_status_log.report_id
              and r.owner_user_id = auth.uid()
        )
    )
);

-- ===================================================================
-- 6. retract_report RPC：analyst 将 submitted/rejected 报告撤回为 draft
-- ===================================================================

create or replace function public.retract_report(
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
    -- 查询报告当前状态和版本号
    select r.status, r.current_version_no
      into v_current_status, v_current_version_no
    from public.report r
    where r.id = p_report_id;

    if not found then
        raise exception '报告不存在: %', p_report_id;
    end if;

    -- 仅 submitted / rejected 可撤回
    if v_current_status not in ('submitted', 'rejected') then
        raise exception '报告状态为 %，无法撤回（仅 submitted/rejected 可撤回）', v_current_status;
    end if;

    v_action_email := auth.jwt() ->> 'email';

    -- 更新状态为 draft（依赖 report_update RLS 的 USING 子句匹配 submitted/rejected 行，
    -- WITH CHECK 要求新状态为 draft，恰好满足）
    update public.report
    set status = 'draft'
    where id = p_report_id;

    -- 写入状态流转日志
    insert into public.report_status_log (
        report_id, from_status, to_status,
        action_by, action_by_name, version_no
    ) values (
        p_report_id, v_current_status, 'draft',
        auth.uid(), v_action_email, v_current_version_no
    );

    return query
        select p_report_id, v_current_version_no, 'draft'::text;
end;
$$;

comment on function public.retract_report is
'将 submitted/rejected 状态的报告撤回为 draft。

权限：仅 analyst 且 report.owner_user_id = auth.uid() 可调用。
      admin 无此需求（admin 可直接 UPDATE）。

校验流程：
  1. 报告必须存在
  2. 当前状态必须为 submitted 或 rejected
  3. 状态流转合法性由 report_status_is_valid + trg_report_status_transition 保证
  4. RLS report_update 的 USING 允许 analyst 找到 submitted/rejected 行
  5. RLS report_update 的 WITH CHECK 要求更新后 status = draft

原子操作：
  UPDATE report.status → INSERT report_status_log，在同一事务内完成。
  任一步失败则整体回滚。

返回：report_id, version_no（撤回时的版本号）, status（固定为 draft）。

依赖：
  - report_status_is_valid 函数（已新增 submitted→draft 路径）
  - report_update RLS（非对称策略，USING 含 submitted/rejected）
  - rsl_insert RLS（已新增 analyst submitted→draft / rejected→draft）';

revoke execute on function public.retract_report from public, anon;
grant execute on function public.retract_report to authenticated;
