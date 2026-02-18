-- Initialize report-type source records in template table.
-- Placeholder rows are intentionally non-active and file_path is empty.

insert into public.template (
  name,
  report_type,
  file_type,
  file_path,
  version,
  is_active,
  uploaded_by
)
select
  src.name,
  src.report_type,
  'word',
  '',
  1,
  false,
  null
from (
  values
    ('Placeholder Company Template', 'company'),
    ('Placeholder Sector Template', 'sector'),
    ('Placeholder Company Flash Template', 'company_flash'),
    ('Placeholder Sector Flash Template', 'sector_flash'),
    ('Placeholder Common Template', 'common')
) as src(name, report_type)
where not exists (
  select 1
  from public.template t
  where t.report_type = src.report_type
);
