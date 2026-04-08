create table public.coverage (
    id uuid not null default gen_random_uuid() primary key,
    ticker text not null,
    english_name text not null,
    chinese_name text,
    traditional_chinese text,
    sector_id uuid not null,
    isin text not null,
    country_of_domicile text not null,
    reporting_currency text,
    is_active boolean not null default true,
    created_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone not null default now()
);

comment on table public.coverage is '公司覆盖（Coverage）主表。记录研究所跟踪的上市公司/标的，包含股票代码（ticker）、公司名称、ISIN、所属行业等核心信息。一个 coverage 代表一个被研究覆盖的标的。';
comment on column public.coverage.id is '公司覆盖 UUID 主键。被 coverage_analyst.coverage_id 和 report.coverage_id 引用';
comment on column public.coverage.ticker is '股票代码/标的代码（唯一），如 "0700.HK"、"600519.SH"';
comment on column public.coverage.english_name is '公司英文全称，如 "Tencent Holdings Ltd"';
comment on column public.coverage.chinese_name is '公司中文简称，如 "腾讯控股"';
comment on column public.coverage.traditional_chinese is '公司繁体中文名称';
comment on column public.coverage.sector_id is '所属行业 ID，引用 sector.id。表示该标的主要所属的行业分类';
comment on column public.coverage.isin is '国际证券识别码 ISIN（唯一），如 "KYG875721634"';
comment on column public.coverage.country_of_domicile is '注册/所在国家或地区，如 "China"、"Hong Kong"';
comment on column public.coverage.reporting_currency is '财务报告货币，如 "CNY"、"HKD"、"USD"';
comment on column public.coverage.is_active is '是否活跃覆盖。true=正在跟踪，false=已终止覆盖';
comment on column public.coverage.created_at is '记录创建时间（UTC）';
comment on column public.coverage.updated_at is '记录最后更新时间（UTC），由 trg_coverage_updated_at 触发器自动维护';

create index idx_coverage_sector
on public.coverage using btree (sector_id);

create unique index uidx_coverage_isin_upper
on public.coverage using btree (upper(btrim(isin)));

create unique index uidx_coverage_ticker_lower
on public.coverage using btree (lower(btrim(ticker)));

create table public.report (
    id uuid not null default gen_random_uuid() primary key,
    title text not null,
    report_type text not null,
    status text not null default 'draft',
    current_version_no integer not null default 0,
    owner_user_id uuid not null,
    coverage_id uuid,
    ticker text,
    sector_id uuid,
    region_code text,
    rating text,
    target_price numeric,
    investment_thesis text,
    report_language text,
    contact_person text,
    published_by uuid,
    published_at timestamp with time zone,
    created_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone not null default now(),
    constraint report_language_check check (
        (report_language is null)
        or (report_language = any (array['zh'::text, 'en'::text]))
    ),
    constraint report_status_check check (
        status = any (array['draft'::text, 'submitted'::text, 'published'::text, 'rejected'::text])
    ),
    constraint report_target_price_check check (
        (target_price is null) or (target_price > 0::numeric)
    ),
    constraint report_version_no_check check (current_version_no >= 0)
);

comment on table public.report is '研究报告主表。记录每篇研究报告的核心元数据，包括标题、类型、状态、所属覆盖、评级等。状态机控制流转：draft → submitted → published/rejected，rejected → draft。报告不做物理删除。';
comment on column public.report.id is '报告 UUID 主键。被 report_version.report_id、report_analyst.report_id、report_status_log.report_id 引用';
comment on column public.report.title is '报告标题';
comment on column public.report.report_type is '报告类型编码，引用 report_type.report_type，如 company、sector、macro';
comment on column public.report.status is '报告当前状态（默认 draft）。合法值：draft（草稿）、submitted（已提交待审批）、published（已发布）、rejected（已退回）。CHECK 约束限制只能为这四个值';
comment on column public.report.current_version_no is '当前最新版本号（默认 0），每次保存新版本时递增。对应 report_version.version_no';
comment on column public.report.owner_user_id is '报告所有者（创建人）的 UUID，引用 auth.users.id。创建后不可转移';
comment on column public.report.coverage_id is '关联的公司覆盖 ID，引用 coverage.id。表示本报告研究的标的';
comment on column public.report.ticker is '标的股票代码，冗余自 coverage.ticker 或手动填写';
comment on column public.report.sector_id is '关联行业 ID，引用 sector.id。表示报告研究的行业';
comment on column public.report.region_code is '关联区域编码，引用 region.code。表示报告覆盖的市场区域';
comment on column public.report.rating is '投资评级编码，引用 rating.code。如 OUTPERFORM、NEUTRAL、UNDERPERFORM、NON_RATED';
comment on column public.report.target_price is '目标价格（numeric）。CHECK 约束要求必须大于 0';
comment on column public.report.investment_thesis is '投资论点摘要';
comment on column public.report.report_language is '报告语言，仅允许 zh（中文）或 en（英文）';
comment on column public.report.contact_person is '联系人邮箱，引用 analyst.email。报告对外的联系分析师';
comment on column public.report.published_by is '发布操作执行人 UUID，引用 auth.users.id。仅在 submitted → published 状态流转时记录';
comment on column public.report.published_at is '发布时间。仅在 submitted → published 状态流转时记录';
comment on column public.report.created_at is '记录创建时间（UTC）';
comment on column public.report.updated_at is '记录最后更新时间（UTC），由 trg_report_updated_at 触发器自动维护';

create index idx_report_created_at_desc
on public.report using btree (created_at desc);

create index idx_report_owner
on public.report using btree (owner_user_id);

create index idx_report_status
on public.report using btree (status);

create table public.coverage_analyst (
    id uuid not null default gen_random_uuid() primary key,
    coverage_id uuid not null references public.coverage(id) on delete cascade,
    analyst_email text not null,
    created_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone not null default now(),
    author_order integer not null,
    constraint coverage_analyst_uniq_pair unique (coverage_id, analyst_email)
);

comment on table public.coverage_analyst is '覆盖-分析师关联表（多对多）。记录哪些分析师负责跟踪某个公司覆盖（coverage），以及署名排序。每个 coverage 可关联多个分析师，通过 author_order 排序。';
comment on column public.coverage_analyst.id is '关联记录 UUID 主键';
comment on column public.coverage_analyst.coverage_id is '关联的公司覆盖 ID，引用 coverage.id（ON DELETE CASCADE，覆盖删除时级联删除关联分析师）';
comment on column public.coverage_analyst.analyst_email is '分析师邮箱，引用 analyst.email（逻辑外键）。标识负责该覆盖的分析师';
comment on column public.coverage_analyst.created_at is '记录创建时间（UTC）';
comment on column public.coverage_analyst.updated_at is '记录最后更新时间（UTC），由 trg_coverage_analyst_updated_at 触发器自动维护';
comment on column public.coverage_analyst.author_order is '署名排序号，数字越小排名越靠前，用于报告署名顺序展示';

create unique index coverage_analyst_uniq_order
on public.coverage_analyst using btree (coverage_id, author_order);

create table public.report_analyst (
    id uuid not null default gen_random_uuid() primary key,
    report_id uuid not null references public.report(id) on delete cascade,
    analyst_email text not null,
    author_order integer not null,
    created_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone not null default now(),
    constraint report_analyst_uniq_pair unique (report_id, analyst_email)
);

comment on table public.report_analyst is '报告-分析师关联表（多对多）。记录每篇报告的署名分析师列表和排序。与 coverage_analyst 结构类似，但作用域是报告而非覆盖。';
comment on column public.report_analyst.id is '关联记录 UUID 主键';
comment on column public.report_analyst.report_id is '所属报告 ID，引用 report.id（ON DELETE CASCADE）。报告删除时级联删除';
comment on column public.report_analyst.analyst_email is '分析师邮箱，引用 analyst.email（逻辑外键）。标识署名分析师';
comment on column public.report_analyst.author_order is '署名排序号，数字越小排名越靠前';
comment on column public.report_analyst.created_at is '记录创建时间（UTC）';
comment on column public.report_analyst.updated_at is '记录最后更新时间（UTC），由 trg_report_analyst_updated_at 触发器自动维护';

create unique index report_analyst_uniq_order
on public.report_analyst using btree (report_id, author_order);

create table public.report_status_log (
    id uuid not null default gen_random_uuid() primary key,
    report_id uuid not null references public.report(id) on delete cascade,
    from_status text not null,
    to_status text not null,
    action_by uuid not null,
    action_by_name text,
    action_at timestamp with time zone not null default now(),
    reason text,
    version_no integer not null,
    constraint report_status_log_reason_required check (
        (to_status <> 'rejected'::text)
        or ((reason is not null) and (btrim(reason) <> ''::text))
    )
);

comment on table public.report_status_log is '报告状态变更审计日志（append-only，禁止 UPDATE/DELETE）。记录每次状态流转的 from/to、操作人、时间、原因（退回时必填）。用于审批追溯和合规审计。';
comment on column public.report_status_log.id is '日志记录 UUID 主键';
comment on column public.report_status_log.report_id is '关联报告 ID，引用 report.id（ON DELETE CASCADE）';
comment on column public.report_status_log.from_status is '流转前状态，如 draft、submitted、published、rejected';
comment on column public.report_status_log.to_status is '流转后状态，如 submitted、published、rejected、draft';
comment on column public.report_status_log.action_by is '执行状态变更的用户 UUID，引用 auth.users.id';
comment on column public.report_status_log.action_by_name is '执行人姓名，冗余记录方便展示';
comment on column public.report_status_log.action_at is '操作时间（UTC，默认当前时间）';
comment on column public.report_status_log.reason is '退回/审批意见。当 to_status = rejected 时 CHECK 约束要求非空且非空白';
comment on column public.report_status_log.version_no is '操作发生时的报告版本号，对应 report_version.version_no';

create index idx_report_status_log_report
on public.report_status_log using btree (report_id);

create table public.report_version (
    id uuid not null default gen_random_uuid() primary key,
    report_id uuid not null references public.report(id) on delete cascade,
    version_no integer not null,
    snapshot_json jsonb not null default '{}'::jsonb,
    word_file_path text,
    model_file_path text,
    pdf_file_path text,
    created_by uuid not null,
    created_at timestamp with time zone not null default now(),
    constraint report_version_no_check check (version_no >= 1),
    constraint report_version_uniq unique (report_id, version_no)
);

comment on table public.report_version is '报告内容版本快照表（append-only，禁止 UPDATE/DELETE）。每次保存报告时创建一条新版本记录，包含字段快照（snapshot_json）和上传文件路径。用于版本对比和历史追溯。';
comment on column public.report_version.id is '版本记录 UUID 主键';
comment on column public.report_version.report_id is '所属报告 ID，引用 report.id（ON DELETE CASCADE）。报告删除时级联删除所有版本';
comment on column public.report_version.version_no is '版本号（>=1），同一 report_id 内递增。(report_id, version_no) 组合唯一';
comment on column public.report_version.snapshot_json is '版本快照（JSONB），存储保存时报告的所有可读字段的键值对，如 title、ticker、rating 等';
comment on column public.report_version.word_file_path is 'Word 版报告文件在 Storage 中的路径';
comment on column public.report_version.model_file_path is '财务模型文件在 Storage 中的路径';
comment on column public.report_version.pdf_file_path is 'PDF 版报告文件在 Storage 中的路径';
comment on column public.report_version.created_by is '版本创建人 UUID，引用 auth.users.id。记录是哪个用户执行了保存操作';
comment on column public.report_version.created_at is '版本创建时间（UTC）';

create index idx_report_version_report_version_desc
on public.report_version using btree (report_id, version_no desc);
