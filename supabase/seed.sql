-- 默认初始化数据。
-- 该文件遵循 Supabase 默认约定：`supabase/seed.sql`。
-- 仅保留需要随 `supabase db reset` 自动加载的稳定数据。
-- 数据来源：旧本地 Supabase 项目 csysmreidiksphqdihex 的稳定字典表。

-- 初始管理员账号。
-- 注意：这里直接保留了旧库中的密码哈希，属于敏感配置。
-- 首次落库后应尽快通过正常的 Auth 管理流程轮换密码。
insert into auth.users (
    instance_id,
    id,
    aud,
    role,
    email,
    encrypted_password,
    email_confirmed_at,
    invited_at,
    confirmation_token,
    confirmation_sent_at,
    recovery_token,
    recovery_sent_at,
    email_change_token_new,
    email_change,
    email_change_sent_at,
    last_sign_in_at,
    raw_app_meta_data,
    raw_user_meta_data,
    is_super_admin,
    created_at,
    updated_at,
    phone,
    phone_confirmed_at,
    phone_change,
    phone_change_token,
    phone_change_sent_at,
    email_change_token_current,
    email_change_confirm_status,
    banned_until,
    reauthentication_token,
    reauthentication_sent_at,
    is_sso_user,
    deleted_at,
    is_anonymous
)
values (
    '00000000-0000-0000-0000-000000000000',
    '14d7d478-24f2-4a28-a5fa-d3dc3dfbc706',
    'authenticated',
    'authenticated',
    'yangxue@opendelp.com',
    '$2a$06$NC.pQkJYfr8I6PVpbHHg8eZoesWge99orpd5fLvdofyvNK4wMIgxC',
    '2026-04-08 08:46:29.945411+00',
    null,
    '',
    null,
    '',
    null,
    '',
    '',
    null,
    null,
    '{"role": "admin", "provider": "email", "providers": ["email"]}'::jsonb,
    '{"full_name": "杨雪"}'::jsonb,
    null,
    '2026-04-08 08:46:29.945411+00',
    '2026-04-08 08:46:29.945411+00',
    null,
    null,
    '',
    '',
    null,
    '',
    0,
    null,
    '',
    null,
    false,
    null,
    false
)
on conflict (id) do update
set
    aud = excluded.aud,
    role = excluded.role,
    email = excluded.email,
    encrypted_password = excluded.encrypted_password,
    email_confirmed_at = excluded.email_confirmed_at,
    invited_at = excluded.invited_at,
    confirmation_token = excluded.confirmation_token,
    confirmation_sent_at = excluded.confirmation_sent_at,
    recovery_token = excluded.recovery_token,
    recovery_sent_at = excluded.recovery_sent_at,
    email_change_token_new = excluded.email_change_token_new,
    email_change = excluded.email_change,
    email_change_sent_at = excluded.email_change_sent_at,
    last_sign_in_at = excluded.last_sign_in_at,
    raw_app_meta_data = excluded.raw_app_meta_data,
    raw_user_meta_data = excluded.raw_user_meta_data,
    is_super_admin = excluded.is_super_admin,
    updated_at = excluded.updated_at,
    phone = excluded.phone,
    phone_confirmed_at = excluded.phone_confirmed_at,
    phone_change = excluded.phone_change,
    phone_change_token = excluded.phone_change_token,
    phone_change_sent_at = excluded.phone_change_sent_at,
    email_change_token_current = excluded.email_change_token_current,
    email_change_confirm_status = excluded.email_change_confirm_status,
    banned_until = excluded.banned_until,
    reauthentication_token = excluded.reauthentication_token,
    reauthentication_sent_at = excluded.reauthentication_sent_at,
    is_sso_user = excluded.is_sso_user,
    deleted_at = excluded.deleted_at,
    is_anonymous = excluded.is_anonymous;

-- 评级字典
insert into public.rating (name, code, rank)
values
    ('优于大市', 'OUTPERFORM', 1),
    ('中性', 'NEUTRAL', 2),
    ('弱于大市', 'UNDERPERFORM', 3),
    ('未评级', 'NON_RATED', 4)
on conflict (code) do update
set
    name = excluded.name,
    rank = excluded.rank;

-- 区域字典
insert into public.region (name_en, name_cn, code, is_active)
values
    ('China', '中国', 'CN', true),
    ('Hong Kong', '香港', 'HK', true),
    ('India', '印度', 'IN', true),
    ('Japan', '日本', 'JP', true),
    ('South Korea', '韩国', 'KR', true),
    ('Macau', '澳门', 'MO', true),
    ('Taiwan', '台湾', 'TW', true),
    ('United States', '美国', 'US', true)
on conflict (code) do update
set
    name_en = excluded.name_en,
    name_cn = excluded.name_cn,
    is_active = excluded.is_active;

-- 报告类型字典
insert into public.report_type (name, report_type, sort, is_active)
values
    ('公司报告', 'company', 1, true),
    ('行业报告', 'sector', 2, true),
    ('公司快评报告', 'company_flash', 3, true),
    ('行业快评报告', 'sector_flash', 4, true),
    ('宏观报告', 'macro', 5, true),
    ('策略报告', 'strategy', 6, true),
    ('量化报告', 'quantitative', 7, true),
    ('债券报告', 'bond', 8, true)
on conflict (report_type) do update
set
    name = excluded.name,
    sort = excluded.sort,
    is_active = excluded.is_active;

-- 初始模板占位记录
insert into public.report_template (id, report_type, language, template_file_path, schema_file_path)
values
    ('bond_en', 'bond', 'en', '', null),
    ('bond_zh', 'bond', 'zh', '', null),
    ('company_en', 'company', 'en', '', null),
    ('company_zh', 'company', 'zh', '', null),
    ('company_flash_en', 'company_flash', 'en', '', null),
    ('company_flash_zh', 'company_flash', 'zh', '', null),
    ('macro_en', 'macro', 'en', '', null),
    ('macro_zh', 'macro', 'zh', '', null),
    ('quantitative_en', 'quantitative', 'en', '', null),
    ('quantitative_zh', 'quantitative', 'zh', '', null),
    ('sector_en', 'sector', 'en', '', null),
    ('sector_zh', 'sector', 'zh', '', null),
    ('sector_flash_en', 'sector_flash', 'en', '', null),
    ('sector_flash_zh', 'sector_flash', 'zh', '', null),
    ('strategy_en', 'strategy', 'en', '', null),
    ('strategy_zh', 'strategy', 'zh', '', null)
on conflict (id) do update
set
    report_type = excluded.report_type,
    language = excluded.language,
    template_file_path = excluded.template_file_path,
    schema_file_path = excluded.schema_file_path;

-- 行业字典
insert into public.sector (id, level, parent_id, name_en, name_cn, wind_name, is_active)
values
    ('00000000-0000-0000-0000-000000000087'::uuid, 1, null, 'Aerospace and National Defense', '航空航天与国防', '航空航天与国防', true),
    ('00000000-0000-0000-0000-000000000001'::uuid, 1, null, 'Agriculture', '农业', '农业', true),
    ('00000000-0000-0000-0000-000000000002'::uuid, 1, null, 'Automation', '自动化', '自动化', true),
    ('00000000-0000-0000-0000-000000000003'::uuid, 1, null, 'Autos', '汽车', '汽车', true),
    ('00000000-0000-0000-0000-000000000007'::uuid, 1, null, 'Banks', '银行行业', '银行行业', true),
    ('00000000-0000-0000-0000-000000000008'::uuid, 1, null, 'Business Services', '商业服务', '商业服务', true),
    ('00000000-0000-0000-0000-000000000009'::uuid, 1, null, 'Casinos & Gaming', '赌场和博彩', '赌场和博彩', true),
    ('00000000-0000-0000-0000-000000000010'::uuid, 1, null, 'Chemical Engineering', '化工', '化工', true),
    ('00000000-0000-0000-0000-000000000011'::uuid, 1, null, 'Computer & Software', '计算机和软件', '计算机和软件', true),
    ('00000000-0000-0000-0000-000000000012'::uuid, 1, null, 'Construction and Building Materials', '建筑建材', '建筑建材', true),
    ('00000000-0000-0000-0000-000000000013'::uuid, 1, null, 'Discretionary', '可选消费', '可选消费', true),
    ('00000000-0000-0000-0000-000000000018'::uuid, 1, null, 'Education', '教育', '教育', true),
    ('00000000-0000-0000-0000-000000000019'::uuid, 1, null, 'Electronics', '电子', '电子', true),
    ('00000000-0000-0000-0000-000000000076'::uuid, 1, null, 'Energy', '能源', '能源', true),
    ('00000000-0000-0000-0000-000000000025'::uuid, 1, null, 'Health Care', '医疗', '医疗', true),
    ('00000000-0000-0000-0000-000000000090'::uuid, 1, null, 'Industrials', '工业', '工业', true),
    ('00000000-0000-0000-0000-000000000033'::uuid, 1, null, 'Internet', '互联网', '互联网', true),
    ('00000000-0000-0000-0000-000000000039'::uuid, 1, null, 'Light Manufacturing', '轻工业', '轻工业', true),
    ('00000000-0000-0000-0000-000000000040'::uuid, 1, null, 'Machinery', '机械', '机械', true),
    ('00000000-0000-0000-0000-000000000084'::uuid, 1, null, 'Materials', '材料', '材料', true),
    ('00000000-0000-0000-0000-000000000041'::uuid, 1, null, 'Media', '媒体', '媒体', true),
    ('00000000-0000-0000-0000-000000000089'::uuid, 1, null, 'Military', '军工', '军工', true),
    ('00000000-0000-0000-0000-000000000043'::uuid, 1, null, 'Non-Bank Financials', '非银行金融', '非银行金融', true),
    ('00000000-0000-0000-0000-000000000054'::uuid, 1, null, 'Property', '房地产', '房地产', true),
    ('00000000-0000-0000-0000-000000000060'::uuid, 1, null, 'Specialty Finance', '特殊金融', '特殊金融', true),
    ('00000000-0000-0000-0000-000000000061'::uuid, 1, null, 'Staples', '必需消费', '必需消费', true),
    ('00000000-0000-0000-0000-000000000069'::uuid, 1, null, 'Telecom', '通信设备', '通信设备', true),
    ('00000000-0000-0000-0000-000000000070'::uuid, 1, null, 'Transportation', '交通运输', '交通运输', true),
    ('00000000-0000-0000-0000-000000000036'::uuid, 2, '00000000-0000-0000-0000-000000000033'::uuid, 'Ads', '广告营销', '广告营销', true),
    ('00000000-0000-0000-0000-000000000073'::uuid, 2, '00000000-0000-0000-0000-000000000070'::uuid, 'Airlines', '航空公司', '航空公司', true),
    ('00000000-0000-0000-0000-000000000068'::uuid, 2, '00000000-0000-0000-0000-000000000061'::uuid, 'Apparel & Footwear', '服装、鞋类及配饰设计', '服装、鞋类及配饰设计', true),
    ('00000000-0000-0000-0000-000000000015'::uuid, 2, '00000000-0000-0000-0000-000000000013'::uuid, 'Apparel, Footwear & Acc Design', '服装、鞋类及配饰设计', '服装、鞋类及配饰设计', true),
    ('00000000-0000-0000-0000-000000000004'::uuid, 2, '00000000-0000-0000-0000-000000000003'::uuid, 'Auto Parts', '汽车配件', '汽车配件', true),
    ('00000000-0000-0000-0000-000000000005'::uuid, 2, '00000000-0000-0000-0000-000000000003'::uuid, 'Automobiles', '汽车', '汽车', true),
    ('00000000-0000-0000-0000-000000000006'::uuid, 2, '00000000-0000-0000-0000-000000000003'::uuid, 'Automotive Retailers', '汽车零售商', '汽车零售商', true),
    ('00000000-0000-0000-0000-000000000027'::uuid, 2, '00000000-0000-0000-0000-000000000025'::uuid, 'Biotech', '生物科技', '生物科技', true),
    ('00000000-0000-0000-0000-000000000059'::uuid, 2, '00000000-0000-0000-0000-000000000054'::uuid, 'Building Products', '建筑产品', '建筑产品', true),
    ('00000000-0000-0000-0000-000000000082'::uuid, 2, '00000000-0000-0000-0000-000000000012'::uuid, 'Cement', '水泥', '水泥', true),
    ('00000000-0000-0000-0000-000000000078'::uuid, 2, '00000000-0000-0000-0000-000000000076'::uuid, 'Coal', '煤炭', '煤炭', true),
    ('00000000-0000-0000-0000-000000000047'::uuid, 2, '00000000-0000-0000-0000-000000000043'::uuid, 'Commercial Finance', '商业金融', '商业金融', true),
    ('00000000-0000-0000-0000-000000000023'::uuid, 2, '00000000-0000-0000-0000-000000000019'::uuid, 'Communication System', '通讯系统', '通讯系统', true),
    ('00000000-0000-0000-0000-000000000080'::uuid, 2, '00000000-0000-0000-0000-000000000012'::uuid, 'Construction', '建筑', '建筑', true),
    ('00000000-0000-0000-0000-000000000020'::uuid, 2, '00000000-0000-0000-0000-000000000019'::uuid, 'Consumer Electronics', '消费电子', '消费电子', true),
    ('00000000-0000-0000-0000-000000000048'::uuid, 2, '00000000-0000-0000-0000-000000000043'::uuid, 'Consumer Finance', '消费金融', '消费金融', true),
    ('00000000-0000-0000-0000-000000000016'::uuid, 2, '00000000-0000-0000-0000-000000000013'::uuid, 'Consumer Services', '消费服务', '消费服务', true),
    ('00000000-0000-0000-0000-000000000086'::uuid, 2, '00000000-0000-0000-0000-000000000013'::uuid, 'Cosmetics', '化妆品', '化妆品', true),
    ('00000000-0000-0000-0000-000000000032'::uuid, 2, '00000000-0000-0000-0000-000000000025'::uuid, 'Drug Store', '药品店', '药品店', true),
    ('00000000-0000-0000-0000-000000000035'::uuid, 2, '00000000-0000-0000-0000-000000000033'::uuid, 'E-Commerce', '电子商务', '电子商务', true),
    ('00000000-0000-0000-0000-000000000088'::uuid, 2, '00000000-0000-0000-0000-000000000076'::uuid, 'Energy Transition', '能源转型', '能源转型', true),
    ('00000000-0000-0000-0000-000000000075'::uuid, 2, '00000000-0000-0000-0000-000000000084'::uuid, 'Ferrous Metals', '黑色金属', '黑色金属', true),
    ('00000000-0000-0000-0000-000000000062'::uuid, 2, '00000000-0000-0000-0000-000000000061'::uuid, 'Food & Beverage', '食品饮料', '食品饮料', true),
    ('00000000-0000-0000-0000-000000000091'::uuid, 2, '00000000-0000-0000-0000-000000000087'::uuid, 'General Aviation', '通用航空', '通用航空', true),
    ('00000000-0000-0000-0000-000000000029'::uuid, 2, '00000000-0000-0000-0000-000000000025'::uuid, 'Health Care Equipment', '医疗设备', '医疗设备', true),
    ('00000000-0000-0000-0000-000000000030'::uuid, 2, '00000000-0000-0000-0000-000000000025'::uuid, 'Health Care Facilities', '医疗设施', '医疗设施', true),
    ('00000000-0000-0000-0000-000000000028'::uuid, 2, '00000000-0000-0000-0000-000000000025'::uuid, 'Health Care Services', '医疗服务', '医疗服务', true),
    ('00000000-0000-0000-0000-000000000031'::uuid, 2, '00000000-0000-0000-0000-000000000025'::uuid, 'Health Care Supplies', '保健用品', '保健用品', true),
    ('00000000-0000-0000-0000-000000000067'::uuid, 2, '00000000-0000-0000-0000-000000000061'::uuid, 'Home Improvement', '家居装潢', '家居装潢', true),
    ('00000000-0000-0000-0000-000000000017'::uuid, 2, '00000000-0000-0000-0000-000000000013'::uuid, 'Household Appliances', '家用电器与器具', '家用电器与器具', true),
    ('00000000-0000-0000-0000-000000000064'::uuid, 2, '00000000-0000-0000-0000-000000000061'::uuid, 'Household Products', '家用产品', '家用产品', true),
    ('00000000-0000-0000-0000-000000000046'::uuid, 2, '00000000-0000-0000-0000-000000000043'::uuid, 'Institutional Brokerage', '机构经纪商', '机构经纪商', true),
    ('00000000-0000-0000-0000-000000000052'::uuid, 2, '00000000-0000-0000-0000-000000000043'::uuid, 'Investment Management', '投资管理', '投资管理', true),
    ('00000000-0000-0000-0000-000000000044'::uuid, 2, '00000000-0000-0000-0000-000000000043'::uuid, 'Life Insurance', '人寿保险', '人寿保险', true),
    ('00000000-0000-0000-0000-000000000038'::uuid, 2, '00000000-0000-0000-0000-000000000033'::uuid, 'Live Streaming', '流媒体', '流媒体', true),
    ('00000000-0000-0000-0000-000000000072'::uuid, 2, '00000000-0000-0000-0000-000000000070'::uuid, 'Logistics Services', '物流服务', '物流服务', true),
    ('00000000-0000-0000-0000-000000000071'::uuid, 2, '00000000-0000-0000-0000-000000000070'::uuid, 'Marine Shipping', '海运', '海运', true),
    ('00000000-0000-0000-0000-000000000045'::uuid, 2, '00000000-0000-0000-0000-000000000043'::uuid, 'Mortgage Finance', '抵押金融', '抵押金融', true),
    ('00000000-0000-0000-0000-000000000079'::uuid, 2, '00000000-0000-0000-0000-000000000076'::uuid, 'New Energy', '新能源', '新能源', true),
    ('00000000-0000-0000-0000-000000000053'::uuid, 2, '00000000-0000-0000-0000-000000000084'::uuid, 'Non-ferrous Metals', '有色金属', '有色金属', true),
    ('00000000-0000-0000-0000-000000000037'::uuid, 2, '00000000-0000-0000-0000-000000000033'::uuid, 'Online Games', '在线游戏', '在线游戏', true),
    ('00000000-0000-0000-0000-000000000083'::uuid, 2, '00000000-0000-0000-0000-000000000012'::uuid, 'Other Construction', '建筑其他', '建筑其他', true),
    ('00000000-0000-0000-0000-000000000022'::uuid, 2, '00000000-0000-0000-0000-000000000019'::uuid, 'Other Electronic Components', '其他电子元器件', '其他电子元器件', true),
    ('00000000-0000-0000-0000-000000000051'::uuid, 2, '00000000-0000-0000-0000-000000000043'::uuid, 'Other Financial Services', '其他金融服务', '其他金融服务', true),
    ('00000000-0000-0000-0000-000000000034'::uuid, 2, '00000000-0000-0000-0000-000000000033'::uuid, 'Other Internet', '其他互联网', '其他互联网', true),
    ('00000000-0000-0000-0000-000000000049'::uuid, 2, '00000000-0000-0000-0000-000000000043'::uuid, 'P&C Insurance', '财产与意外保险', '财产与意外保险', true),
    ('00000000-0000-0000-0000-000000000063'::uuid, 2, '00000000-0000-0000-0000-000000000061'::uuid, 'Packaged Food', '包装食品', '包装食品', true),
    ('00000000-0000-0000-0000-000000000024'::uuid, 2, '00000000-0000-0000-0000-000000000019'::uuid, 'PCB', '印刷电路板', '印刷电路板', true),
    ('00000000-0000-0000-0000-000000000077'::uuid, 2, '00000000-0000-0000-0000-000000000076'::uuid, 'Petroleum and Petrochemical', '石油石化', '石油石化', true),
    ('00000000-0000-0000-0000-000000000026'::uuid, 2, '00000000-0000-0000-0000-000000000025'::uuid, 'Pharmaceuticals', '药品', '药品', true),
    ('00000000-0000-0000-0000-000000000081'::uuid, 2, '00000000-0000-0000-0000-000000000012'::uuid, 'Plastic Pipe', '塑料管', '塑料管', true),
    ('00000000-0000-0000-0000-000000000057'::uuid, 2, '00000000-0000-0000-0000-000000000054'::uuid, 'Property Management', '房地产服务', '房地产服务', true),
    ('00000000-0000-0000-0000-000000000085'::uuid, 2, '00000000-0000-0000-0000-000000000070'::uuid, 'Rail & Road', '铁路和公路', '铁路和公路', true),
    ('00000000-0000-0000-0000-000000000056'::uuid, 2, '00000000-0000-0000-0000-000000000054'::uuid, 'Real Estate Development', '房地产开发', '房地产开发', true),
    ('00000000-0000-0000-0000-000000000066'::uuid, 2, '00000000-0000-0000-0000-000000000061'::uuid, 'Restaurants', '餐饮业', '餐饮业', true),
    ('00000000-0000-0000-0000-000000000014'::uuid, 2, '00000000-0000-0000-0000-000000000013'::uuid, 'Retail', '零售', '零售', true),
    ('00000000-0000-0000-0000-000000000021'::uuid, 2, '00000000-0000-0000-0000-000000000019'::uuid, 'Semiconductor', '半导体', '半导体', true),
    ('00000000-0000-0000-0000-000000000065'::uuid, 2, '00000000-0000-0000-0000-000000000061'::uuid, 'Tobacco', '烟草', '烟草', true),
    ('00000000-0000-0000-0000-000000000050'::uuid, 2, '00000000-0000-0000-0000-000000000043'::uuid, 'Wealth Management', '财富管理', '财富管理', true)
on conflict (id) do update
set
    level = excluded.level,
    parent_id = excluded.parent_id,
    name_en = excluded.name_en,
    name_cn = excluded.name_cn,
    wind_name = excluded.wind_name,
    is_active = excluded.is_active;
