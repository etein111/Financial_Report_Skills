-- Storage bucket for templates
-- This migration creates the templates bucket and configures access policies

-- Create templates bucket (if not exists)
insert into storage.buckets (id, name, public)
values ('templates', 'templates', false)
on conflict (id) do nothing;

-- Policy: Authenticated users can read templates
create policy storage_templates_select_authenticated
on storage.objects
for select
to authenticated
using (bucket_id = 'templates');

-- Policy: Only admin can upload templates
create policy storage_templates_insert_admin
on storage.objects
for insert
to authenticated
with check (
  bucket_id = 'templates'
  and (auth.jwt()->'app_metadata'->>'role') = 'admin'
);

-- Policy: Only admin can update templates
create policy storage_templates_update_admin
on storage.objects
for update
to authenticated
using (
  bucket_id = 'templates'
  and (auth.jwt()->'app_metadata'->>'role') = 'admin'
)
with check (
  bucket_id = 'templates'
  and (auth.jwt()->'app_metadata'->>'role') = 'admin'
);

-- Policy: Only admin can delete templates
create policy storage_templates_delete_admin
on storage.objects
for delete
to authenticated
using (
  bucket_id = 'templates'
  and (auth.jwt()->'app_metadata'->>'role') = 'admin'
);
