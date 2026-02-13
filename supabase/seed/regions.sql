insert into public.region (name, code)
values
  ('China', 'CN'),
  ('Hong Kong', 'HK'),
  ('Japan', 'JP'),
  ('Taiwan', 'TW'),
  ('Korea', 'KR'),
  ('India', 'IN'),
  ('Macau', 'MO'),
  ('US', 'US')
on conflict (name) do update
set code = excluded.code,
    updated_at = timezone('Asia/Shanghai', now());

