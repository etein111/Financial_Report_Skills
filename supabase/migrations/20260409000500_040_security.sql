grant usage on schema public to anon, authenticated, service_role;

alter table public.analyst enable row level security;
alter table public.rating enable row level security;
alter table public.region enable row level security;
alter table public.report_type enable row level security;
alter table public.report_template enable row level security;
alter table public.sector enable row level security;
alter table public.coverage enable row level security;
alter table public.coverage_analyst enable row level security;
alter table public.report enable row level security;
alter table public.report_analyst enable row level security;
alter table public.report_status_log enable row level security;
alter table public.report_version enable row level security;

create policy dict_select
on public.analyst
for select
to authenticated
using (true);

create policy dict_write
on public.analyst
to authenticated
using (public.current_app_role() = 'admin'::text)
with check (public.current_app_role() = 'admin'::text);

create policy dict_select
on public.rating
for select
to authenticated
using (true);

create policy dict_write
on public.rating
to authenticated
using (public.current_app_role() = 'admin'::text)
with check (public.current_app_role() = 'admin'::text);

create policy dict_select
on public.region
for select
to authenticated
using (true);

create policy dict_write
on public.region
to authenticated
using (public.current_app_role() = 'admin'::text)
with check (public.current_app_role() = 'admin'::text);

create policy dict_select
on public.report_type
for select
to authenticated
using (true);

create policy dict_write
on public.report_type
to authenticated
using (public.current_app_role() = 'admin'::text)
with check (public.current_app_role() = 'admin'::text);

create policy dict_select
on public.report_template
for select
to authenticated
using (true);

create policy dict_write
on public.report_template
to authenticated
using (public.current_app_role() = 'admin'::text)
with check (public.current_app_role() = 'admin'::text);

create policy dict_select
on public.sector
for select
to authenticated
using (true);

create policy dict_write
on public.sector
to authenticated
using (public.current_app_role() = 'admin'::text)
with check (public.current_app_role() = 'admin'::text);

create policy coverage_select
on public.coverage
for select
to authenticated
using (true);

create policy coverage_insert
on public.coverage
for insert
to authenticated
with check (public.current_app_role() = any (array['admin'::text, 'sa'::text, 'analyst'::text]));

create policy coverage_update
on public.coverage
for update
to authenticated
using (public.current_app_role() = 'admin'::text)
with check (public.current_app_role() = 'admin'::text);

create policy coverage_delete
on public.coverage
for delete
to authenticated
using (public.current_app_role() = 'admin'::text);

create policy cov_analyst_select
on public.coverage_analyst
for select
to authenticated
using (true);

create policy cov_analyst_insert
on public.coverage_analyst
for insert
to authenticated
with check (public.current_app_role() = any (array['admin'::text, 'sa'::text, 'analyst'::text]));

create policy cov_analyst_update
on public.coverage_analyst
for update
to authenticated
using (public.current_app_role() = 'admin'::text)
with check (public.current_app_role() = 'admin'::text);

create policy cov_analyst_delete
on public.coverage_analyst
for delete
to authenticated
using (public.current_app_role() = 'admin'::text);

create policy report_select
on public.report
for select
to authenticated
using (
    (public.current_app_role() = 'admin'::text)
    or (
        (public.current_app_role() = 'sa'::text)
        and (status = any (array['submitted'::text, 'published'::text, 'rejected'::text]))
    )
    or (
        (public.current_app_role() = 'analyst'::text)
        and (owner_user_id = auth.uid())
    )
);

create policy report_insert
on public.report
for insert
to authenticated
with check (
    (public.current_app_role() = 'admin'::text)
    or (
        (public.current_app_role() = 'analyst'::text)
        and (owner_user_id = auth.uid())
    )
);

create policy report_update
on public.report
for update
to authenticated
using (
    (public.current_app_role() = 'admin'::text)
    or (
        (public.current_app_role() = 'analyst'::text)
        and (owner_user_id = auth.uid())
        and (status = any (array['draft'::text, 'submitted'::text]))
    )
)
with check (
    (public.current_app_role() = 'admin'::text)
    or (
        (public.current_app_role() = 'analyst'::text)
        and (owner_user_id = auth.uid())
        and (status = any (array['draft'::text, 'submitted'::text]))
    )
);

create policy report_delete
on public.report
for delete
to authenticated
using (public.current_app_role() = 'admin'::text);

create policy ra_select
on public.report_analyst
for select
to authenticated
using (
    exists (
        select 1
        from public.report r
        where r.id = report_analyst.report_id
          and (
              (public.current_app_role() = 'admin'::text)
              or (
                  (public.current_app_role() = 'sa'::text)
                  and (r.status = any (array['submitted'::text, 'published'::text, 'rejected'::text]))
              )
              or (
                  (public.current_app_role() = 'analyst'::text)
                  and (r.owner_user_id = auth.uid())
              )
          )
    )
);

create policy ra_insert
on public.report_analyst
for insert
to authenticated
with check (
    exists (
        select 1
        from public.report r
        where r.id = report_analyst.report_id
          and (
              (public.current_app_role() = 'admin'::text)
              or (
                  (public.current_app_role() = 'analyst'::text)
                  and (r.owner_user_id = auth.uid())
                  and (r.status = any (array['draft'::text, 'submitted'::text]))
              )
          )
    )
);

create policy rsl_select
on public.report_status_log
for select
to authenticated
using (
    exists (
        select 1
        from public.report r
        where r.id = report_status_log.report_id
          and (
              (public.current_app_role() = 'admin'::text)
              or (
                  (public.current_app_role() = 'sa'::text)
                  and (r.status = any (array['submitted'::text, 'published'::text, 'rejected'::text]))
              )
              or (
                  (public.current_app_role() = 'analyst'::text)
                  and (r.owner_user_id = auth.uid())
              )
          )
    )
);

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
        and (from_status = 'draft'::text)
        and (to_status = 'submitted'::text)
        and exists (
            select 1
            from public.report r
            where r.id = report_status_log.report_id
              and r.owner_user_id = auth.uid()
        )
    )
);

create policy rv_select
on public.report_version
for select
to authenticated
using (
    exists (
        select 1
        from public.report r
        where r.id = report_version.report_id
          and (
              (public.current_app_role() = 'admin'::text)
              or (
                  (public.current_app_role() = 'sa'::text)
                  and (r.status = any (array['submitted'::text, 'published'::text, 'rejected'::text]))
              )
              or (
                  (public.current_app_role() = 'analyst'::text)
                  and (r.owner_user_id = auth.uid())
              )
          )
    )
);

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
                  and (r.status = any (array['draft'::text, 'submitted'::text]))
              )
          )
    )
);

grant all on function public.current_app_role() to anon, authenticated, service_role;
grant all on function public.report_status_is_valid(text, text) to anon, authenticated, service_role;
grant all on function public.set_updated_at_utc() to anon, authenticated, service_role;
grant all on function public.validate_sector_hierarchy() to anon, authenticated, service_role;
grant all on function public.report_enforce_status_transition() to anon, authenticated, service_role;

grant all on table public.analyst to anon, authenticated, service_role;
grant all on table public.coverage to anon, authenticated, service_role;
grant all on table public.coverage_analyst to anon, authenticated, service_role;
grant all on table public.rating to anon, authenticated, service_role;
grant all on table public.region to anon, authenticated, service_role;
grant all on table public.report to anon, authenticated, service_role;
grant all on table public.report_analyst to anon, authenticated, service_role;
grant all on table public.report_status_log to anon, authenticated, service_role;
grant all on table public.report_template to anon, authenticated, service_role;
grant all on table public.report_type to anon, authenticated, service_role;
grant all on table public.report_version to anon, authenticated, service_role;
grant all on table public.sector to anon, authenticated, service_role;
