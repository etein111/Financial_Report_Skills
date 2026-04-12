-- 20260413000200_111_remove_rejected_to_submitted.sql
-- 移除 rejected → submitted 直接重提路径
--
-- 业务规则：rejected 报告必须先撤回为 draft，再从 draft 重新提交。
-- 不允许 rejected 直接跳到 submitted。
--
-- 变更：report_status_is_valid 函数中 rejected 的合法目标从 ('draft', 'submitted') 收窄为 ('draft')

create or replace function public.report_status_is_valid(from_status text, to_status text)
returns boolean
language sql
immutable
as $$
    select (from_status = 'draft' and to_status = 'submitted')
        or (from_status = 'submitted' and to_status in ('published', 'rejected', 'draft'))
        or (from_status = 'rejected' and to_status = 'draft')
$$;

comment on function public.report_status_is_valid(text, text) is
'判断报告状态流转是否合法（IMMUTABLE）。

合法路径：
  draft → submitted          （analyst 提交审阅）
  submitted → published      （sa 发布）
  submitted → rejected       （sa 退回）
  submitted → draft          （analyst 撤回，由 retract_report RPC 调用）
  rejected → draft           （analyst 撤回，由 retract_report RPC 调用）

所有其他路径均为非法，report_enforce_status_transition 触发器会在
UPDATE report 时调用本函数进行校验，非法流转将抛出异常。';
