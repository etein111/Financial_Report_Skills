-- 20260409000610_055_storage_policies.sql
-- Storage bucket RLS 策略：templates 和 reports bucket

-- -------------------------------------------------------------------
-- templates bucket
-- -------------------------------------------------------------------

-- 所有已认证用户可读取模板文件（用于生成报告）
create policy templates_select
on storage.objects
for select
to authenticated
using (bucket_id = 'templates');

-- 仅 admin 可上传/更新/删除模板文件
create policy templates_insert
on storage.objects
for insert
to authenticated
with check (
    bucket_id = 'templates'
    and public.current_app_role() = 'admin'
);

create policy templates_update
on storage.objects
for update
to authenticated
using (
    bucket_id = 'templates'
    and public.current_app_role() = 'admin'
);

create policy templates_delete
on storage.objects
for delete
to authenticated
using (
    bucket_id = 'templates'
    and public.current_app_role() = 'admin'
);

-- -------------------------------------------------------------------
-- reports bucket
-- -------------------------------------------------------------------

-- admin 可读取所有报告文件；analyst 可读取自己的；sa 可读取 submitted/published/rejected
create policy reports_select
on storage.objects
for select
to authenticated
using (
    bucket_id = 'reports'
    and (
        public.current_app_role() = 'admin'
        or exists (
            select 1
            from public.report r
            where
                -- storage path 以 {report_id}/ 开头，取第一段作为 report_id
                r.id::text = split_part(name, '/', 1)
                and (
                    (public.current_app_role() = 'analyst' and r.owner_user_id = auth.uid())
                    or (
                        public.current_app_role() = 'sa'
                        and r.status = any(array['submitted', 'published', 'rejected'])
                    )
                )
        )
    )
);

-- admin 可上传/更新所有报告文件；analyst 可上传自己 draft 的文件
create policy reports_insert
on storage.objects
for insert
to authenticated
with check (
    bucket_id = 'reports'
    and (
        public.current_app_role() = 'admin'
        or exists (
            select 1
            from public.report r
            where
                r.id::text = split_part(name, '/', 1)
                and public.current_app_role() = 'analyst'
                and r.owner_user_id = auth.uid()
                and r.status = any(array['draft', 'submitted'])
        )
    )
);

create policy reports_update
on storage.objects
for update
to authenticated
using (
    bucket_id = 'reports'
    and (
        public.current_app_role() = 'admin'
        or exists (
            select 1
            from public.report r
            where
                r.id::text = split_part(name, '/', 1)
                and public.current_app_role() = 'analyst'
                and r.owner_user_id = auth.uid()
                and r.status = any(array['draft', 'submitted'])
        )
    )
);

create policy reports_delete
on storage.objects
for delete
to authenticated
using (
    bucket_id = 'reports'
    and public.current_app_role() = 'admin'
);
