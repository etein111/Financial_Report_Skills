-- 测试数据。
-- 默认不随 `supabase db reset` 自动执行，按需手工导入。
-- 使用方法：supabase db reset 之后，psql -f supabase/tests/test_data.sql
--
-- 本文件包含：
--   1. 测试用户（admin / sa / analyst x3）
--   2. 分析师档案（对应上面的用户 + 额外 2 名不关联 auth 的分析师）
--   3. 覆盖标的（Vistra Corp / Bloom Energy / VRT / 西锐飞机 / 腾讯 / GE Vernova）
--   4. 覆盖-分析师关联
--   5. 报告（公司报告 x4 / 公司快评 x1 / 行业快评 x1 / 宏观报告 x1）
--   6. 报告状态流转日志

-- ============================================================
-- 0. 密码规则：各用户密码 = 邮箱地址，方便记忆
-- ============================================================

-- ============================================================
-- 1. 测试用户（auth.users）
-- ============================================================

-- admin（已有 seed 中的 yangxue@opendelp.com，这里再加一个备用 admin）
insert into auth.users (
    instance_id, id, aud, role, email, encrypted_password,
    email_confirmed_at, confirmation_token, recovery_token,
    email_change_token_new, email_change, email_change_token_current,
    email_change_confirm_status,
    raw_app_meta_data, raw_user_meta_data,
    created_at, updated_at,
    is_sso_user, is_anonymous
) values (
    '00000000-0000-0000-0000-000000000000',
    'a0000000-0000-0000-0000-000000000001'::uuid,
    'authenticated', 'authenticated',
    'admin@test.com',
    '$2b$06$4lg0vKb.3zYB/2r58FmzoOxsZTjvuWuCJz.sQdqY3HVV4T6Sag8U6',
    now(), '', '', '', '', '', 0,
    '{"role": "admin", "provider": "email", "providers": ["email"]}'::jsonb,
    '{"full_name": "测试管理员"}'::jsonb,
    now(), now(), false, false
) on conflict (id) do update set
    encrypted_password = excluded.encrypted_password;

-- SA（审批角色）
insert into auth.users (
    instance_id, id, aud, role, email, encrypted_password,
    email_confirmed_at, confirmation_token, recovery_token,
    email_change_token_new, email_change, email_change_token_current,
    email_change_confirm_status,
    raw_app_meta_data, raw_user_meta_data,
    created_at, updated_at,
    is_sso_user, is_anonymous
) values (
    '00000000-0000-0000-0000-000000000000',
    'a0000000-0000-0000-0000-000000000002'::uuid,
    'authenticated', 'authenticated',
    'sa@test.com',
    '$2b$06$ONiy4cC5rvvN3Q0xzmESUO3oh.gZFftOLnVg9YQAT2Ph.J2W15EY.',
    now(), '', '', '', '', '', 0,
    '{"role": "sa", "provider": "email", "providers": ["email"]}'::jsonb,
    '{"full_name": "测试审批员"}'::jsonb,
    now(), now(), false, false
) on conflict (id) do update set
    encrypted_password = excluded.encrypted_password;

-- analyst 1 —— 杨斌（Bin Yang）
insert into auth.users (
    instance_id, id, aud, role, email, encrypted_password,
    email_confirmed_at, confirmation_token, recovery_token,
    email_change_token_new, email_change, email_change_token_current,
    email_change_confirm_status,
    raw_app_meta_data, raw_user_meta_data,
    created_at, updated_at,
    is_sso_user, is_anonymous
) values (
    '00000000-0000-0000-0000-000000000000',
    'a0000000-0000-0000-0000-000000000010'::uuid,
    'authenticated', 'authenticated',
    'harryyang@hfisec.com.hk',
    '$2b$06$ZErqP8gYPH2fbycT2fntU.NDI/A.8iQlmn3bHXgrqGEb26px4pGB6',
    now(), '', '', '', '', '', 0,
    '{"role": "analyst", "provider": "email", "providers": ["email"]}'::jsonb,
    '{"full_name": "杨斌"}'::jsonb,
    now(), now(), false, false
) on conflict (id) do update set
    encrypted_password = excluded.encrypted_password;

-- analyst 2 —— 邓轶达（Yida Deng）
insert into auth.users (
    instance_id, id, aud, role, email, encrypted_password,
    email_confirmed_at, confirmation_token, recovery_token,
    email_change_token_new, email_change, email_change_token_current,
    email_change_confirm_status,
    raw_app_meta_data, raw_user_meta_data,
    created_at, updated_at,
    is_sso_user, is_anonymous
) values (
    '00000000-0000-0000-0000-000000000000',
    'a0000000-0000-0000-0000-000000000011'::uuid,
    'authenticated', 'authenticated',
    'dengyida@hfisec.com.hk',
    '$2b$06$sxdS3mFXOypAzBB.p/5NbOjPsXb6ngtz/KlXc5Eyji5KZkCl/E5py',
    now(), '', '', '', '', '', 0,
    '{"role": "analyst", "provider": "email", "providers": ["email"]}'::jsonb,
    '{"full_name": "邓轶达"}'::jsonb,
    now(), now(), false, false
) on conflict (id) do update set
    encrypted_password = excluded.encrypted_password;

-- analyst 3 —— 李明（Ming Li）
insert into auth.users (
    instance_id, id, aud, role, email, encrypted_password,
    email_confirmed_at, confirmation_token, recovery_token,
    email_change_token_new, email_change, email_change_token_current,
    email_change_confirm_status,
    raw_app_meta_data, raw_user_meta_data,
    created_at, updated_at,
    is_sso_user, is_anonymous
) values (
    '00000000-0000-0000-0000-000000000000',
    'a0000000-0000-0000-0000-000000000012'::uuid,
    'authenticated', 'authenticated',
    'mingli@hfisec.com.hk',
    '$2b$06$.o10m6rfAflv/.sgr8LSVuCYG0NO1YelxoIWzWEXaemjZwDHZrlB6',
    now(), '', '', '', '', '', 0,
    '{"role": "analyst", "provider": "email", "providers": ["email"]}'::jsonb,
    '{"full_name": "李明"}'::jsonb,
    now(), now(), false, false
) on conflict (id) do update set
    encrypted_password = excluded.encrypted_password;


-- ============================================================
-- 2. 分析师档案（public.analyst）
-- ============================================================

insert into public.analyst (english_name, chinese_name, email, suffix, sfc, region_code, is_active)
values
    ('Bin Yang',     '杨斌',   'harryyang@hfisec.com.hk', 'CFA',  'BSQ313', 'HK', true),
    ('Yida Deng',    '邓轶达', 'dengyida@hfisec.com.hk',  null,    'BVF321', 'HK', true),
    ('Ming Li',      '李明',   'mingli@hfisec.com.hk',    'FRM',   'BQR789', 'HK', true),
    ('Xue Yang',     '杨雪',   'yangxue@opendelp.com',    null,    null,     'HK', true),
    ('Wei Zhang',    '张伟',   'weizhang@hfisec.com.hk',  null,    'BCD456', 'US', true)
on conflict (email) do update set
    english_name = excluded.english_name,
    chinese_name = excluded.chinese_name,
    suffix       = excluded.suffix,
    sfc          = excluded.sfc,
    region_code  = excluded.region_code,
    is_active    = excluded.is_active;


-- ============================================================
-- 3. 覆盖标的（public.coverage）
-- ============================================================
-- 行业 ID 引用 seed.sql 中的 sector：
--   Energy                 = '00000000-0000-0000-0000-000000000076'
--   New Energy (子行业)     = '00000000-0000-0000-0000-000000000079'
--   Energy Transition (子)  = '00000000-0000-0000-0000-000000000088'
--   Electronics            = '00000000-0000-0000-0000-000000000019'
--   Semiconductor (子)      = '00000000-0000-0000-0000-000000000021'
--   Internet               = '00000000-0000-0000-0000-000000000033'
--   E-Commerce (子)         = '00000000-0000-0000-0000-000000000035'
--   Aerospace & Defense    = '00000000-0000-0000-0000-000000000087'
--   General Aviation (子)   = '00000000-0000-0000-0000-000000000091'
--   Industrials            = '00000000-0000-0000-0000-000000000090'

insert into public.coverage (id, ticker, english_name, chinese_name, traditional_chinese, sector_id, isin, country_of_domicile, reporting_currency, is_active)
values
    ('c0000000-0000-0000-0000-000000000001'::uuid,
     'VST US', 'Vistra Corp', '维斯特拉', null,
     '00000000-0000-0000-0000-000000000079'::uuid,
     'US92810W1037', 'US', 'USD', true),

    ('c0000000-0000-0000-0000-000000000002'::uuid,
     'BE US', 'Bloom Energy Corp', '布鲁姆能源', null,
     '00000000-0000-0000-0000-000000000088'::uuid,
     'US09363Q1053', 'US', 'USD', true),

    ('c0000000-0000-0000-0000-000000000003'::uuid,
     'VRT US', 'Vertiv Holdings', '维谛技术', null,
     '00000000-0000-0000-0000-000000000021'::uuid,
     'US92542V1053', 'US', 'USD', true),

    ('c0000000-0000-0000-0000-000000000004'::uuid,
     '2507.HK', 'Cirrus Aircraft', '西锐飞机', '西銳飛機',
     '00000000-0000-0000-0000-000000000091'::uuid,
     'HK0000250712', 'HK', 'HKD', true),

    ('c0000000-0000-0000-0000-000000000005'::uuid,
     '0700.HK', 'Tencent Holdings', '腾讯控股', '騰訊控股',
     '00000000-0000-0000-0000-000000000035'::uuid,
     'KYG875721634', 'HK', 'HKD', true),

    ('c0000000-0000-0000-0000-000000000006'::uuid,
     'GEV US', 'GE Vernova', 'GE维诺瓦', null,
     '00000000-0000-0000-0000-000000000090'::uuid,
     'US36267V1038', 'US', 'USD', true)
on conflict (id) do update set
    ticker              = excluded.ticker,
    english_name        = excluded.english_name,
    chinese_name        = excluded.chinese_name,
    traditional_chinese = excluded.traditional_chinese,
    sector_id           = excluded.sector_id,
    isin                = excluded.isin,
    country_of_domicile = excluded.country_of_domicile,
    reporting_currency  = excluded.reporting_currency,
    is_active           = excluded.is_active;


-- ============================================================
-- 4. 覆盖-分析师关联（public.coverage_analyst）
-- ============================================================

insert into public.coverage_analyst (coverage_id, analyst_email, author_order)
values
    ('c0000000-0000-0000-0000-000000000001'::uuid, 'harryyang@hfisec.com.hk', 1),
    ('c0000000-0000-0000-0000-000000000002'::uuid, 'harryyang@hfisec.com.hk', 1),
    ('c0000000-0000-0000-0000-000000000003'::uuid, 'harryyang@hfisec.com.hk', 1),
    ('c0000000-0000-0000-0000-000000000003'::uuid, 'dengyida@hfisec.com.hk',  2),
    ('c0000000-0000-0000-0000-000000000004'::uuid, 'harryyang@hfisec.com.hk', 1),
    ('c0000000-0000-0000-0000-000000000005'::uuid, 'dengyida@hfisec.com.hk',  1),
    ('c0000000-0000-0000-0000-000000000005'::uuid, 'mingli@hfisec.com.hk',    2),
    ('c0000000-0000-0000-0000-000000000006'::uuid, 'harryyang@hfisec.com.hk', 1),
    ('c0000000-0000-0000-0000-000000000006'::uuid, 'dengyida@hfisec.com.hk',  2)
on conflict (coverage_id, analyst_email) do update set
    author_order = excluded.author_order;


-- ============================================================
-- 5. 报告（public.report）
-- ============================================================
-- 状态覆盖 4 种：published / submitted / draft / rejected

-- 5a. Vistra Corp 首次覆盖 —— 已发布（英文）
insert into public.report (
    id, title, report_type, status, word_path, pdf_path, model_path,
    owner_user_id, coverage_id, ticker,
    sector_id, region_code, rating, target_price,
    investment_thesis, report_language, contact_person,
    lead_analyst_email, analyst_emails,
    published_by, published_at
) values (
    'e0000000-0000-0000-0000-000000000001'::uuid,
    'Active Response to Energy Transition and Enhancement of Low-Carbon Power Amid AI Data Center Migration and Natural Gas Demand Growth: Initiation',
    'company', 'published',
    'reports/e0000000-0000-0000-0000-000000000001/report/20260104_163000/EN-Vistra_Corp20260104.docx',
    'reports/e0000000-0000-0000-0000-000000000001/report/20260104_163000/EN-Vistra_Corp20260104.pdf',
    'reports/e0000000-0000-0000-0000-000000000001/model/20260104_163000/EN-Vistra_Corp20260104.xlsx',
    'a0000000-0000-0000-0000-000000000010'::uuid,
    'c0000000-0000-0000-0000-000000000001'::uuid,
    'VST US',
    '00000000-0000-0000-0000-000000000079'::uuid,
    'US', 'OUTPERFORM', 423.72,
    'Vistra is well positioned as a leading integrated power generator benefiting from AI data center demand growth and energy transition.',
    'en', 'harryyang@hfisec.com.hk',
    'harryyang@hfisec.com.hk', ARRAY['harryyang@hfisec.com.hk'],
    'a0000000-0000-0000-0000-000000000002'::uuid,
    '2026-01-05 10:00:00+00'
) on conflict (id) do nothing;

-- 5b. 西锐飞机首次覆盖 —— 已发布（中文）
insert into public.report (
    id, title, report_type, status, word_path, pdf_path, model_path,
    owner_user_id, coverage_id, ticker,
    sector_id, region_code, rating, target_price,
    investment_thesis, report_language, contact_person,
    lead_analyst_email, analyst_emails,
    published_by, published_at
) values (
    'e0000000-0000-0000-0000-000000000002'::uuid,
    '首次覆盖：安全、创新与强大生态系统铸就西锐私人航空全球领导者地位',
    'company', 'published',
    'reports/e0000000-0000-0000-0000-000000000002/report/20251020_180000/西锐飞机首次覆盖报告.docx',
    'reports/e0000000-0000-0000-0000-000000000002/report/20251020_180000/西锐飞机首次覆盖报告.pdf',
    null,
    'a0000000-0000-0000-0000-000000000010'::uuid,
    'c0000000-0000-0000-0000-000000000004'::uuid,
    '2507.HK',
    '00000000-0000-0000-0000-000000000091'::uuid,
    'HK', 'OUTPERFORM', 86.72,
    '西锐飞机凭借卓越的安全记录、持续创新能力及完善的私人航空生态系统，成为全球私人航空领域的领导者。',
    'zh', 'harryyang@hfisec.com.hk',
    'harryyang@hfisec.com.hk', ARRAY['harryyang@hfisec.com.hk'],
    'a0000000-0000-0000-0000-000000000002'::uuid,
    '2025-10-21 10:00:00+00'
) on conflict (id) do nothing;

-- 5c. Bloom Energy 公司报告 —— 待审批（submitted）
insert into public.report (
    id, title, report_type, status, word_path, pdf_path, model_path,
    owner_user_id, coverage_id, ticker,
    sector_id, region_code, rating, target_price,
    investment_thesis, report_language, contact_person,
    lead_analyst_email, analyst_emails
) values (
    'e0000000-0000-0000-0000-000000000003'::uuid,
    'Bloom Energy: Solid Oxide Fuel Cell Leader Entering Multi-Year Growth Cycle',
    'company', 'submitted',
    'reports/e0000000-0000-0000-0000-000000000003/report/20260305_110000/Bloom_Energy_v2.docx',
    'reports/e0000000-0000-0000-0000-000000000003/report/20260305_110000/Bloom_Energy_v2.pdf',
    'reports/e0000000-0000-0000-0000-000000000003/model/20260305_110000/Bloom_Energy_v2.xlsx',
    'a0000000-0000-0000-0000-000000000010'::uuid,
    'c0000000-0000-0000-0000-000000000002'::uuid,
    'BE US',
    '00000000-0000-0000-0000-000000000088'::uuid,
    'US', 'NEUTRAL', 28.50,
    'Bloom Energy is transitioning from a project-driven business to a recurring revenue model with its solid oxide fuel cell platform.',
    'en', 'harryyang@hfisec.com.hk',
    'harryyang@hfisec.com.hk', ARRAY['harryyang@hfisec.com.hk']
) on conflict (id) do nothing;

-- 5d. VRT 公司报告 —— 草稿（draft）
insert into public.report (
    id, title, report_type, status, word_path, pdf_path, model_path,
    owner_user_id, coverage_id, ticker,
    sector_id, region_code, rating, target_price,
    investment_thesis, report_language, contact_person,
    lead_analyst_email, analyst_emails
) values (
    'e0000000-0000-0000-0000-000000000004'::uuid,
    'Vertiv Holdings: AI Infrastructure Enabler Poised for Accelerating Growth',
    'company', 'draft',
    null, null, null,
    'a0000000-0000-0000-0000-000000000011'::uuid,
    'c0000000-0000-0000-0000-000000000003'::uuid,
    'VRT US',
    '00000000-0000-0000-0000-000000000021'::uuid,
    'US', 'OUTPERFORM', 155.00,
    'Vertiv is a key beneficiary of AI-driven data center buildout with leading thermal management and power infrastructure solutions.',
    'en', 'dengyida@hfisec.com.hk',
    'dengyida@hfisec.com.hk', ARRAY['dengyida@hfisec.com.hk', 'harryyang@hfisec.com.hk']
) on conflict (id) do nothing;

-- 5e. 全球消费及互联网周报（sector_flash） —— 已发布
insert into public.report (
    id, title, report_type, status, word_path, pdf_path, model_path,
    owner_user_id, coverage_id, ticker,
    sector_id, region_code, rating,
    investment_thesis, report_language, contact_person,
    lead_analyst_email, analyst_emails,
    published_by, published_at
) values (
    'e0000000-0000-0000-0000-000000000005'::uuid,
    '周报(03/16-03/19): 消费板块：港股消费震荡，油价高企压制风险偏好；海外互联网板块：腾讯年报落地，AI长期逻辑未变',
    'sector_flash', 'published',
    'reports/e0000000-0000-0000-0000-000000000005/report/20260319_170000/全球消费及互联网周报.docx',
    'reports/e0000000-0000-0000-0000-000000000005/report/20260319_170000/全球消费及互联网周报.pdf',
    null,
    'a0000000-0000-0000-0000-000000000010'::uuid,
    null, null,
    '00000000-0000-0000-0000-000000000033'::uuid,
    'HK', 'NON_RATED',
    '港股消费板块震荡反弹，海外互联网板块腾讯年报落地，AI长期逻辑持续强化。',
    'zh', 'harryyang@hfisec.com.hk',
    'harryyang@hfisec.com.hk', ARRAY['harryyang@hfisec.com.hk'],
    'a0000000-0000-0000-0000-000000000002'::uuid,
    '2026-03-20 10:00:00+00'
) on conflict (id) do nothing;

-- 5f. 斯卡吉特河水电项目宏观报告（macro） —— 已发布
insert into public.report (
    id, title, report_type, status, word_path, pdf_path, model_path,
    owner_user_id, coverage_id, ticker,
    sector_id, region_code, rating,
    investment_thesis, report_language, contact_person,
    lead_analyst_email, analyst_emails,
    published_by, published_at
) values (
    'e0000000-0000-0000-0000-000000000006'::uuid,
    '斯卡吉特河水电项目重新许可：和解达成的里程碑与ESG三方博弈的深度透视',
    'macro', 'published',
    'reports/e0000000-0000-0000-0000-000000000006/report/20260316_200000/0317斯卡吉特河水电项目.docx',
    'reports/e0000000-0000-0000-0000-000000000006/report/20260316_200000/0317斯卡吉特河水电项目.pdf',
    null,
    'a0000000-0000-0000-0000-000000000010'::uuid,
    null, null,
    '00000000-0000-0000-0000-000000000076'::uuid,
    'US', 'NON_RATED',
    '斯卡吉特河水电项目重新许可标志北美公用事业资产估值发生结构性重塑，水电资产从低成本能源向高合规资产转型。',
    'zh', 'harryyang@hfisec.com.hk',
    'harryyang@hfisec.com.hk', ARRAY['harryyang@hfisec.com.hk'],
    'a0000000-0000-0000-0000-000000000002'::uuid,
    '2026-03-17 10:00:00+00'
) on conflict (id) do nothing;

-- 5g. 腾讯 Q4 业绩快评（company_flash） —— 被退回（rejected）
insert into public.report (
    id, title, report_type, status, word_path, pdf_path, model_path,
    owner_user_id, coverage_id, ticker,
    sector_id, region_code, rating, target_price,
    investment_thesis, report_language, contact_person,
    lead_analyst_email, analyst_emails
) values (
    'e0000000-0000-0000-0000-000000000007'::uuid,
    'Tencent Q4 FY2025 Earnings Flash: Revenue Beat but AI Capex Guidance Disappoints',
    'company_flash', 'rejected',
    'reports/e0000000-0000-0000-0000-000000000007/report/20260320_150000/Tencent_Q4_Flash.docx',
    'reports/e0000000-0000-0000-0000-000000000007/report/20260320_150000/Tencent_Q4_Flash.pdf',
    null,
    'a0000000-0000-0000-0000-000000000011'::uuid,
    'c0000000-0000-0000-0000-000000000005'::uuid,
    '0700.HK',
    '00000000-0000-0000-0000-000000000035'::uuid,
    'HK', 'OUTPERFORM', 520.00,
    '腾讯Q4收入超预期但AI资本开支指引低于市场预期，短期承压但长期AI商业化逻辑不变。',
    'en', 'dengyida@hfisec.com.hk',
    'dengyida@hfisec.com.hk', ARRAY['dengyida@hfisec.com.hk']
) on conflict (id) do nothing;


-- ============================================================
-- 6. 报告状态流转日志（public.report_status_log）
-- ============================================================
-- 注意：report 表有 BEFORE UPDATE 触发器校验状态流转合法性，
-- 但 report_status_log 是普通插入，无额外触发器。
-- rejected 状态的 reason 字段不能为空。

-- Vistra: draft -> submitted -> published
insert into public.report_status_log (id, report_id, from_status, to_status, action_by, action_by_name, action_at)
values
    ('b0000000-0000-0000-0000-000000000001'::uuid,
     'e0000000-0000-0000-0000-000000000001'::uuid,
     'draft', 'submitted',
     'a0000000-0000-0000-0000-000000000010'::uuid, 'Bin Yang',
     '2026-01-04 16:30:00+00'),

    ('b0000000-0000-0000-0000-000000000002'::uuid,
     'e0000000-0000-0000-0000-000000000001'::uuid,
     'submitted', 'published',
     'a0000000-0000-0000-0000-000000000002'::uuid, '测试审批员',
      '2026-01-05 10:00:00+00')
on conflict (id) do nothing;

-- 西锐飞机: draft -> submitted -> published
insert into public.report_status_log (id, report_id, from_status, to_status, action_by, action_by_name, action_at)
values
    ('b0000000-0000-0000-0000-000000000003'::uuid,
     'e0000000-0000-0000-0000-000000000002'::uuid,
     'draft', 'submitted',
     'a0000000-0000-0000-0000-000000000010'::uuid, 'Bin Yang',
     '2025-10-20 18:00:00+00'),

    ('b0000000-0000-0000-0000-000000000004'::uuid,
     'e0000000-0000-0000-0000-000000000002'::uuid,
     'submitted', 'published',
     'a0000000-0000-0000-0000-000000000002'::uuid, '测试审批员',
      '2025-10-21 10:00:00+00')
on conflict (id) do nothing;

-- Bloom Energy: draft -> submitted (v1) -> rejected -> draft -> submitted (v2)
insert into public.report_status_log (id, report_id, from_status, to_status, action_by, action_by_name, reason, action_at)
values
    ('b0000000-0000-0000-0000-000000000005'::uuid,
     'e0000000-0000-0000-0000-000000000003'::uuid,
     'draft', 'submitted',
     'a0000000-0000-0000-0000-000000000010'::uuid, 'Bin Yang', null,
     '2026-03-01 09:00:00+00'),

    ('b0000000-0000-0000-0000-000000000006'::uuid,
     'e0000000-0000-0000-0000-000000000003'::uuid,
     'submitted', 'rejected',
     'a0000000-0000-0000-0000-000000000002'::uuid, '测试审批员',
     '目标价格缺少估值方法论说明，请补充 DCF 假设。',
     '2026-03-02 14:00:00+00'),

    ('b0000000-0000-0000-0000-000000000007'::uuid,
     'e0000000-0000-0000-0000-000000000003'::uuid,
     'rejected', 'draft',
     'a0000000-0000-0000-0000-000000000010'::uuid, 'Bin Yang', null,
     '2026-03-03 10:00:00+00'),

    ('b0000000-0000-0000-0000-000000000008'::uuid,
     'e0000000-0000-0000-0000-000000000003'::uuid,
     'draft', 'submitted',
     'a0000000-0000-0000-0000-000000000010'::uuid, 'Bin Yang', null,
      '2026-03-05 11:00:00+00')
on conflict (id) do nothing;

-- 行业快报: draft -> submitted -> published
insert into public.report_status_log (id, report_id, from_status, to_status, action_by, action_by_name, action_at)
values
    ('b0000000-0000-0000-0000-000000000009'::uuid,
     'e0000000-0000-0000-0000-000000000005'::uuid,
     'draft', 'submitted',
     'a0000000-0000-0000-0000-000000000010'::uuid, 'Bin Yang',
     '2026-03-19 17:00:00+00'),

    ('b0000000-0000-0000-0000-000000000010'::uuid,
     'e0000000-0000-0000-0000-000000000005'::uuid,
     'submitted', 'published',
     'a0000000-0000-0000-0000-000000000002'::uuid, '测试审批员',
      '2026-03-20 10:00:00+00')
on conflict (id) do nothing;

-- 宏观报告: draft -> submitted -> published
insert into public.report_status_log (id, report_id, from_status, to_status, action_by, action_by_name, action_at)
values
    ('b0000000-0000-0000-0000-000000000011'::uuid,
     'e0000000-0000-0000-0000-000000000006'::uuid,
     'draft', 'submitted',
     'a0000000-0000-0000-0000-000000000010'::uuid, 'Bin Yang',
     '2026-03-16 20:00:00+00'),

    ('b0000000-0000-0000-0000-000000000012'::uuid,
     'e0000000-0000-0000-0000-000000000006'::uuid,
     'submitted', 'published',
     'a0000000-0000-0000-0000-000000000002'::uuid, '测试审批员',
      '2026-03-17 10:00:00+00')
on conflict (id) do nothing;

-- 腾讯快评: draft -> submitted -> rejected
insert into public.report_status_log (id, report_id, from_status, to_status, action_by, action_by_name, reason, action_at)
values
    ('b0000000-0000-0000-0000-000000000013'::uuid,
     'e0000000-0000-0000-0000-000000000007'::uuid,
     'draft', 'submitted',
     'a0000000-0000-0000-0000-000000000011'::uuid, 'Yida Deng', null,
     '2026-03-20 15:00:00+00'),

    ('b0000000-0000-0000-0000-000000000014'::uuid,
     'e0000000-0000-0000-0000-000000000007'::uuid,
     'submitted', 'rejected',
     'a0000000-0000-0000-0000-000000000002'::uuid, '测试审批员',
     '快评篇幅过长，请精简至两页以内并补充关键财务指标对比表。',
      '2026-03-21 09:30:00+00')
on conflict (id) do nothing;


-- ============================================================
-- 9. 威胜控股测试数据（coverage + 两份报告）
-- ============================================================

-- 9a. coverage: 威胜控股（3393.HK）
insert into public.coverage (id, ticker, english_name, chinese_name, traditional_chinese, sector_id, isin, country_of_domicile, reporting_currency, is_active)
values (
    'c0000000-0000-0000-0000-000000000007'::uuid,
    '3393.HK', 'Wasion Holdings', '威胜控股', '威勝控股',
    '00000000-0000-0000-0000-000000000088'::uuid,
    'HK0000033938', 'HK', 'HKD', true
) on conflict (id) do update set
    ticker              = excluded.ticker,
    english_name        = excluded.english_name,
    chinese_name        = excluded.chinese_name,
    traditional_chinese = excluded.traditional_chinese,
    sector_id           = excluded.sector_id,
    isin                = excluded.isin,
    country_of_domicile = excluded.country_of_domicile,
    reporting_currency  = excluded.reporting_currency,
    is_active           = excluded.is_active;

-- 9b. coverage_analyst
insert into public.coverage_analyst (coverage_id, analyst_email, author_order)
values
    ('c0000000-0000-0000-0000-000000000007'::uuid, 'harryyang@hfisec.com.hk', 1),
    ('c0000000-0000-0000-0000-000000000007'::uuid, 'dengyida@hfisec.com.hk',  2)
on conflict (coverage_id, analyst_email) do update set
    author_order = excluded.author_order;

-- 9c. 报告 1：威胜控股首次覆盖 —— 已发布（2025-07-25, 目标价 120, OUTPERFORM）
insert into public.report (
    id, title, report_type, status, word_path, pdf_path, model_path,
    owner_user_id, coverage_id, ticker,
    sector_id, region_code, rating, target_price,
    investment_thesis, report_language, contact_person,
    lead_analyst_email, analyst_emails,
    published_by, published_at
) values (
    'e0000000-0000-0000-0000-000000000008'::uuid,
    '威胜控股（3393.HK）首次覆盖：配网投资与AI算力双轮驱动，能源计量龙头再启航',
    'company', 'published',
    'reports/e0000000-0000-0000-0000-000000000008/report/20250724_180000/威胜控股首次覆盖.docx',
    'reports/e0000000-0000-0000-0000-000000000008/report/20250724_180000/威胜控股首次覆盖.pdf',
    'reports/e0000000-0000-0000-0000-000000000008/model/20250724_180000/威胜控股首次覆盖.xlsx',
    'a0000000-0000-0000-0000-000000000010'::uuid,
    'c0000000-0000-0000-0000-000000000007'::uuid,
    '3393.HK',
    '00000000-0000-0000-0000-000000000088'::uuid,
    'HK', 'OUTPERFORM', 120.00,
    '配网投资高景气叠加AI算力用电需求爆发，威胜作为能源计量龙头，智能电表海外拓展加速，业绩进入新一轮增长周期。',
    'zh', 'harryyang@hfisec.com.hk',
    'harryyang@hfisec.com.hk', ARRAY['harryyang@hfisec.com.hk', 'dengyida@hfisec.com.hk'],
    'a0000000-0000-0000-0000-000000000002'::uuid,
    '2025-07-25 10:00:00+00'
) on conflict (id) do nothing;

-- 9d. 报告 2：威胜控股更新报告 —— 已发布（2025-10-25, 目标价 140, NEUTRAL）
insert into public.report (
    id, title, report_type, status, word_path, pdf_path, model_path,
    owner_user_id, coverage_id, ticker,
    sector_id, region_code, rating, target_price,
    investment_thesis, report_language, contact_person,
    lead_analyst_email, analyst_emails,
    published_by, published_at
) values (
    'e0000000-0000-0000-0000-000000000009'::uuid,
    '威胜控股（3393.HK）更新：海外订单放缓拖累短期增速，下调评级至中性',
    'company', 'published',
    'reports/e0000000-0000-0000-0000-000000000009/report/20251024_180000/威胜控股更新.docx',
    'reports/e0000000-0000-0000-0000-000000000009/report/20251024_180000/威胜控股更新.pdf',
    null,
    'a0000000-0000-0000-0000-000000000010'::uuid,
    'c0000000-0000-0000-0000-000000000007'::uuid,
    '3393.HK',
    '00000000-0000-0000-0000-000000000088'::uuid,
    'HK', 'NEUTRAL', 140.00,
    '海外市场拓展节奏放缓，国内配网招标竞争加剧，短期增速承压；上调目标价至140港元反映估值切换，但下调评级至中性。',
    'zh', 'harryyang@hfisec.com.hk',
    'harryyang@hfisec.com.hk', ARRAY['harryyang@hfisec.com.hk', 'dengyida@hfisec.com.hk'],
    'a0000000-0000-0000-0000-000000000002'::uuid,
    '2025-10-25 10:00:00+00'
) on conflict (id) do nothing;

-- 9g. report_status_log
-- 威胜首次覆盖: draft -> submitted -> published (2025-07-25)
insert into public.report_status_log (id, report_id, from_status, to_status, action_by, action_by_name, action_at)
values
    ('b0000000-0000-0000-0000-000000000015'::uuid,
     'e0000000-0000-0000-0000-000000000008'::uuid,
     'draft', 'submitted',
     'a0000000-0000-0000-0000-000000000010'::uuid, 'Bin Yang',
     '2025-07-24 18:00:00+00'),

    ('b0000000-0000-0000-0000-000000000016'::uuid,
     'e0000000-0000-0000-0000-000000000008'::uuid,
     'submitted', 'published',
     'a0000000-0000-0000-0000-000000000002'::uuid, '测试审批员',
     '2025-07-25 10:00:00+00')
on conflict (id) do nothing;

-- 威胜更新报告: draft -> submitted -> published (2025-10-25)
insert into public.report_status_log (id, report_id, from_status, to_status, action_by, action_by_name, action_at)
values
    ('b0000000-0000-0000-0000-000000000017'::uuid,
     'e0000000-0000-0000-0000-000000000009'::uuid,
     'draft', 'submitted',
     'a0000000-0000-0000-0000-000000000010'::uuid, 'Bin Yang',
     '2025-10-24 18:00:00+00'),

    ('b0000000-0000-0000-0000-000000000018'::uuid,
     'e0000000-0000-0000-0000-000000000009'::uuid,
     'submitted', 'published',
     'a0000000-0000-0000-0000-000000000002'::uuid, '测试审批员',
     '2025-10-25 10:00:00+00')
on conflict (id) do nothing;
