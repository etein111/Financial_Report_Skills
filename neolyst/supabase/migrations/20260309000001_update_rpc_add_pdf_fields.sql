-- Update report_save_content_atomic RPC function: add pdf_file_path and pdf_file_name

-- Drop the old function first (to avoid function signature conflict)
drop function if exists public.report_save_content_atomic(uuid, text, text, text, text, numeric, text, uuid, text, uuid, text, boolean, uuid, jsonb, uuid, text, text, text, text, text, text);

create or replace function public.report_save_content_atomic(
  p_report_id uuid,
  p_title text,
  p_report_type text,
  p_ticker text,
  p_rating text,
  p_target_price text,
  p_region_code text,
  p_sector_id uuid,
  p_report_language text,
  p_contact_person_id uuid,
  p_investment_thesis text,
  p_certificate_confirmed boolean,
  p_coverage_id uuid,
  p_analysts jsonb,
  p_changed_by uuid,
  p_word_file_path text,
  p_pdf_file_path text,
  p_model_file_path text,
  p_word_file_name text,
  p_pdf_file_name text,
  p_model_file_name text
)
returns public.report
language plpgsql
security invoker
set search_path = public
as $$
declare
  v_report public.report;
  v_current_version_no integer;
  v_updated public.report;
begin
  -- 获取当前版本号
  select current_version_no into v_current_version_no
  from public.report
  where id = p_report_id;

  if not found then
    raise exception 'Report not found';
  end if;

  -- 更新 report 表
  update public.report
  set
    title = p_title,
    report_type = p_report_type,
    ticker = p_ticker,
    rating = p_rating,
    target_price = case when p_target_price is null or p_target_price = '' then null else p_target_price::numeric end,
    region_code = p_region_code,
    sector_id = p_sector_id,
    report_language = p_report_language,
    contact_person_id = p_contact_person_id,
    investment_thesis = p_investment_thesis,
    certificate_confirmed = p_certificate_confirmed,
    coverage_id = p_coverage_id,
    current_version_no = v_current_version_no + 1,
    updated_at = now()
  where id = p_report_id
  returning * into v_report;

  -- 插入新版本记录
  insert into public.report_version (
    id,
    report_id,
    version_no,
    snapshot_json,
    word_file_path,
    pdf_file_path,
    model_file_path,
    word_file_name,
    pdf_file_name,
    model_file_name,
    changed_by,
    changed_at,
    created_at
  ) values (
    gen_random_uuid(),
    p_report_id,
    v_current_version_no + 1,
    jsonb_build_object(
      'title', p_title,
      'report_type', p_report_type,
      'ticker', p_ticker,
      'rating', p_rating,
      'target_price', p_target_price,
      'region_code', p_region_code,
      'sector_id', p_sector_id,
      'report_language', p_report_language,
      'contact_person_id', p_contact_person_id,
      'investment_thesis', p_investment_thesis,
      'certificate_confirmed', p_certificate_confirmed,
      'coverage_id', p_coverage_id,
      'analysts', p_analysts
    ),
    p_word_file_path,
    p_pdf_file_path,
    p_model_file_path,
    p_word_file_name,
    p_pdf_file_name,
    p_model_file_name,
    p_changed_by,
    now(),
    now()
  );

  -- 删除旧的 analyst 关联并插入新的
  delete from public.report_analyst where report_id = p_report_id;

  if p_analysts is not null and jsonb_array_length(p_analysts) > 0 then
    insert into public.report_analyst (id, report_id, analyst_id, role, sort_order, created_at, updated_at)
    select
      gen_random_uuid(),
      p_report_id,
      (elem->>'analyst_id')::uuid,
      (elem->>'role')::smallint,
      (elem->>'sort_order')::smallint,
      now(),
      now()
    from jsonb_array_elements(p_analysts) as elem;
  end if;

  return v_report;
end;
$$;
