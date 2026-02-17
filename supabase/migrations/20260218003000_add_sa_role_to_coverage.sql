-- Add 'sa' role to coverage and coverage_analyst RLS policies
-- SA (Senior Analyst) should have same permissions as Analyst for coverage

-- Drop and recreate coverage INSERT policy
drop policy if exists coverage_insert_admin_analyst on public.coverage;
create policy coverage_insert_admin_analyst
on public.coverage
for insert
to authenticated
with check ((auth.jwt()->'app_metadata'->>'role') in ('admin', 'sa', 'analyst'));

-- Drop and recreate coverage_analyst INSERT policy
drop policy if exists coverage_analyst_insert_admin_analyst on public.coverage_analyst;
create policy coverage_analyst_insert_admin_analyst
on public.coverage_analyst
for insert
to authenticated
with check ((auth.jwt()->'app_metadata'->>'role') in ('admin', 'sa', 'analyst'));
