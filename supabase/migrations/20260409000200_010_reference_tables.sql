create table public.analyst (
    english_name text not null,
    chinese_name text,
    email text not null primary key,
    suffix text,
    sfc text,
    region_code text,
    is_active boolean not null default true,
    created_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone not null default now(),
    constraint analyst_email_lowercase_check check (email = lower(email))
);

comment on table public.analyst is '分析师业务信息表。存储分析师的姓名、邮箱、所属区域、资质证书等信息，与 auth.users 解耦——认证信息由 Supabase Auth 管理，业务属性在此表维护。通过 email 字段（小写）与 auth.users.email 逻辑关联。';
comment on column public.analyst.english_name is '分析师英文全名，如 "John Smith"';
comment on column public.analyst.chinese_name is '分析师中文姓名';
comment on column public.analyst.email is '分析师邮箱（唯一）。强制小写存储（CHECK 约束 email = lower(email)）。作为与 auth.users 的逻辑关联键，也用于 coverage_analyst.analyst_email 和 report_analyst.analyst_email 的关联';
comment on column public.analyst.suffix is '姓名后缀/头衔，如 "CFA"、"FRM"';
comment on column public.analyst.sfc is '证券期货从业资格编号（中国证监会 SFC 编号）';
comment on column public.analyst.region_code is '分析师所属区域编码，引用 region.code，如 CN、HK';
comment on column public.analyst.is_active is '是否在职。true=在职，false=已离职或停用';
comment on column public.analyst.created_at is '记录创建时间（UTC）';
comment on column public.analyst.updated_at is '记录最后更新时间（UTC），由 trg_analyst_updated_at 触发器自动维护';

create table public.rating (
    name text not null,
    code text not null unique,
    rank integer not null default 1 primary key
);

comment on table public.rating is '评级字典表。存储研究报告中给出的投资评级，如"优于大市/中性/弱于大市/未评级"。报告的 report.rating 字段引用此表 report_rating.code。';
comment on column public.rating.name is '评级的中文显示名称，如"优于大市"、"中性"、"弱于大市"、"未评级"';
comment on column public.rating.code is '评级的英文编码（唯一），如 OUTPERFORM、NEUTRAL、UNDERPERFORM、NON_RATED。报告 report.rating 字段存储此编码值';
comment on column public.rating.rank is '排序权重，值越小排名越靠前，用于前端下拉排序展示';

create table public.region (
    name_en text not null unique,
    name_cn text not null unique,
    code text not null primary key,
    is_active boolean not null default true,
    created_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone not null default now()
);

comment on table public.region is '区域/市场字典表。存储研究所覆盖的亚太及全球市场区域，如中国、香港、日本、台湾、韩国、印度、澳门、美国。分析师和报告通过 region_code 字段关联此表 region.code。';
comment on column public.region.name_en is '区域英文名称（唯一），如 China、Hong Kong';
comment on column public.region.name_cn is '区域中文名称（唯一），如 中国、香港';
comment on column public.region.code is '区域标准编码（唯一），如 CN、HK、JP、TW。分析师 analyst.region_code 和报告 report.region_code 存储此编码值';
comment on column public.region.is_active is '是否启用。false 表示已停用，不再出现在下拉选项中';
comment on column public.region.created_at is '记录创建时间（UTC）';
comment on column public.region.updated_at is '记录最后更新时间（UTC），由 updated_at 触发器自动维护';

create table public.report_type (
    name text not null,
    report_type text not null primary key,
    sort integer not null default 1,
    is_active boolean not null default true,
    created_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone not null default now()
);

comment on table public.report_type is '报告类型字典表。定义研究报告的分类，如"公司报告"(company)、"行业报告"(sector)、"宏观报告"(macro) 等。每条记录包含中英文名称和排序权重。';
comment on column public.report_type.name is '报告类型的中文名称（如"公司报告"）';
comment on column public.report_type.report_type is '报告类型的英文编码（如 company、sector、macro），用于 report.report_type 和 report_template.report_type 的关联';
comment on column public.report_type.sort is '排序权重，值越小越靠前，用于前端下拉选项排序';
comment on column public.report_type.is_active is '是否启用。false 表示已停用，不再出现在下拉选项中';
comment on column public.report_type.created_at is '记录创建时间（UTC）';
comment on column public.report_type.updated_at is '记录最后更新时间（UTC），由 trg_report_type_updated_at 触发器自动维护';

create table public.report_template (
    id text not null primary key,
    report_type text not null,
    language text not null default 'en',
    template_file_path text not null,
    schema_file_path text,
    created_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone not null default now(),
    constraint template_language_check check (language = any (array['en'::text, 'zh'::text]))
);

comment on table public.report_template is '报告模板配置表。每种 report_type × language 组合对应一个模板记录，记录模板文件和 schema 文件的存储路径。系统初始化时预置占位模板（template_file_path 为空字符串），Admin 上传真实文件后覆盖。';
comment on column public.report_template.id is '模板标识（文本主键），通常由 report_type + language 组合生成，如 "company_en"、"sector_zh"';
comment on column public.report_template.report_type is '所属报告类型编码，引用 report_type.report_type，如 company、sector';
comment on column public.report_template.language is '模板语言编码，仅允许 en（英文）或 zh（中文）';
comment on column public.report_template.template_file_path is '模板文件在 Storage 中的存储路径。初始化占位模板为空字符串';
comment on column public.report_template.schema_file_path is '模板对应的 JSON Schema 文件路径，用于前端表单校验';
comment on column public.report_template.created_at is '记录创建时间（UTC）';
comment on column public.report_template.updated_at is '记录最后更新时间（UTC），由 trg_template_updated_at 触发器自动维护';

create index idx_template_group
on public.report_template using btree (report_type, language);

create table public.sector (
    id uuid not null default gen_random_uuid() primary key,
    level smallint not null,
    parent_id uuid,
    name_en text not null,
    name_cn text,
    wind_name text,
    is_active boolean not null default true,
    created_at timestamp with time zone not null default now(),
    updated_at timestamp with time zone not null default now(),
    constraint sector_level_check check (level = any (array[1, 2])),
    constraint sector_level_parent_check check (
        ((level = 1) and (parent_id is null))
        or ((level = 2) and (parent_id is not null))
    )
);

comment on table public.sector is '行业分类字典表。采用两级树结构：level=1 为一级行业（如"金融"），level=2 为二级行业（如"银行"），通过 parent_id 挂载到一级行业。报告和公司覆盖通过 sector_id 字段引用此表。约束：level=1 必须无父节点，level=2 必须有父节点。';
comment on column public.sector.id is '行业 UUID 主键。被 coverage.sector_id 和 report.sector_id 引用';
comment on column public.sector.level is '层级，仅允许 1（一级行业）或 2（二级行业）。CHECK 约束强制 level=1 时 parent_id 必须为 NULL，level=2 时 parent_id 必须非 NULL';
comment on column public.sector.parent_id is '父级行业 ID（仅 level=2 时有值），引用 sector.id。level=1 的行此字段为 NULL';
comment on column public.sector.name_en is '行业英文名称';
comment on column public.sector.name_cn is '行业中文名称';
comment on column public.sector.wind_name is '万得（Wind）行业分类体系中的对应名称，用于与外部数据源对齐';
comment on column public.sector.is_active is '是否启用。false 表示已停用，不再出现在下拉选项中';
comment on column public.sector.created_at is '记录创建时间（UTC）';
comment on column public.sector.updated_at is '记录最后更新时间（UTC），由 trg_sector_updated_at 触发器自动维护';

create index idx_sector_active
on public.sector using btree (is_active);

create index idx_sector_level_parent
on public.sector using btree (level, parent_id);

create unique index uidx_sector_l1_name_en
on public.sector using btree (lower(name_en))
where parent_id is null;

create unique index uidx_sector_l2_parent_name_en
on public.sector using btree (parent_id, lower(name_en))
where parent_id is not null;
