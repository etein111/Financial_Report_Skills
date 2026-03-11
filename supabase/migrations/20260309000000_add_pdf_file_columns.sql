-- Add pdf_file_path and pdf_file_name columns to report_version table
-- This separates PDF files from Word/PPT files

alter table public.report_version
add column if not exists pdf_file_path text,
add column if not exists pdf_file_name text;

-- Add index for pdf_file_path
create index if not exists idx_report_version_pdf_file_path
on public.report_version(pdf_file_path)
where pdf_file_path is not null;
