create or replace function public.validate_sector_hierarchy()
returns trigger
language plpgsql
as $$
declare
  v_parent_level smallint;
  v_parent_parent uuid;
begin
  if new.parent_id is not null and new.parent_id = new.id then
    raise exception 'sector parent cannot reference itself';
  end if;

  if new.level = 1 then
    if new.parent_id is not null then
      raise exception 'level 1 sector cannot have parent';
    end if;
    return new;
  end if;

  select s.level, s.parent_id
    into v_parent_level, v_parent_parent
  from public.sector s
  where s.id = new.parent_id;

  if not found then
    raise exception 'level 2 sector must reference an existing parent';
  end if;

  if v_parent_level <> 1 then
    raise exception 'level 2 sector parent must be level 1';
  end if;

  if v_parent_parent is not null then
    raise exception 'sector hierarchy supports only two levels';
  end if;

  return new;
end;
$$;

comment on function public.validate_sector_hierarchy() is '行业分类层级校验触发器函数（BEFORE INSERT OR UPDATE）。强制执行：1）禁止自引用（parent_id ≠ id）；2）level=1 不允许有 parent_id；3）level=2 的 parent_id 必须指向已存在的 level=1 行；4）最多两级，禁止更深层级。由 trg_sector_hierarchy 触发器绑定到 sector 表。';

create or replace function public.report_enforce_status_transition()
returns trigger
language plpgsql
as $$
begin
  if tg_op = 'UPDATE' and new.status is distinct from old.status then
    if not public.report_status_is_valid(old.status, new.status) then
      raise exception 'invalid report status transition: % -> %', old.status, new.status;
    end if;
  end if;
  return new;
end;
$$;

comment on function public.report_enforce_status_transition() is '报告状态流转强制校验触发器函数（BEFORE UPDATE）。当 report.status 发生变化时，调用 report_status_is_valid() 校验流转合法性，非法时抛出异常阻止写入。由 trg_report_status_transition 触发器绑定到 report 表。';

create or replace trigger trg_analyst_updated_at
before update on public.analyst
for each row
execute function public.set_updated_at_utc();

create or replace trigger trg_coverage_updated_at
before update on public.coverage
for each row
execute function public.set_updated_at_utc();

create or replace trigger trg_coverage_analyst_updated_at
before update on public.coverage_analyst
for each row
execute function public.set_updated_at_utc();

create or replace trigger trg_region_updated_at
before update on public.region
for each row
execute function public.set_updated_at_utc();

create or replace trigger trg_report_updated_at
before update on public.report
for each row
execute function public.set_updated_at_utc();

create or replace trigger trg_report_status_transition
before update on public.report
for each row
execute function public.report_enforce_status_transition();

create or replace trigger trg_report_analyst_updated_at
before update on public.report_analyst
for each row
execute function public.set_updated_at_utc();

create or replace trigger trg_template_updated_at
before update on public.report_template
for each row
execute function public.set_updated_at_utc();

create or replace trigger trg_report_type_updated_at
before update on public.report_type
for each row
execute function public.set_updated_at_utc();

create or replace trigger trg_sector_hierarchy
before insert or update on public.sector
for each row
execute function public.validate_sector_hierarchy();

create or replace trigger trg_sector_updated_at
before update on public.sector
for each row
execute function public.set_updated_at_utc();
