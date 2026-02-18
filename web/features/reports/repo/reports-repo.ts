import "server-only";

import type {
  ReportAnalystInput,
  ReportFileLabel,
  ReportStatus,
  ReportType,
} from "@/domain/schemas/report";
import { err, ok, type Result } from "@/lib/result";
import type { PaginatedList } from "@/lib/pagination";
import { createServerClient } from "@/lib/supabase/server";
import {
  buildReportStoragePath as buildReportStoragePathValue,
  getFileExtension as getFileExtensionValue,
  validateUploadExtension as validateUploadExtensionValue,
  toUtcTimestamp as toUtcTimestampValue,
} from "@/features/reports/file-utils";

const PAGE_SIZE = 15;

export type ReportAnalyst = {
  id: string;
  report_id: string;
  analyst_id: string;
  role: number;
  sort_order: number;
  created_at: string;
  updated_at: string;
  analyst?: {
    id: string;
    full_name: string;
    chinese_name: string | null;
    email: string;
  };
};

export type ReportVersion = {
  id: string;
  report_id: string;
  version_no: number;
  snapshot_json: Record<string, unknown>;
  word_file_path: string | null;
  model_file_path: string | null;
  changed_by: string;
  changed_at: string;
  created_at: string;
};

export type ReportStatusLog = {
  id: string;
  report_id: string;
  from_status: ReportStatus;
  to_status: ReportStatus;
  action_by: string;
  action_at: string;
  reason: string | null;
  version_no: number;
  created_at: string;
};

export type ReportSummary = {
  id: string;
  owner_user_id: string;
  title: string;
  report_type: ReportType;
  status: ReportStatus;
  current_version_no: number;
  coverage_id: string | null;
  sector_id: string | null;
  published_by: string | null;
  published_at: string | null;
  created_at: string;
  updated_at: string;
  analysts: ReportAnalyst[];
};

export type ReportDetail = ReportSummary & {
  coverage?: {
    id: string;
    ticker: string;
    english_full_name: string;
  } | null;
  sector?: {
    id: string;
    name_en: string;
    name_cn: string | null;
  } | null;
  versions: ReportVersion[];
  latest_version: ReportVersion | null;
  status_logs: ReportStatusLog[];
};

export type CreateReportParams = {
  owner_user_id: string;
  title: string;
  report_type: ReportType;
  coverage_id?: string | null;
  sector_id?: string | null;
  analysts: ReportAnalystInput[];
};

export type SaveReportContentParams = {
  report_id: string;
  title: string;
  report_type: ReportType;
  coverage_id?: string | null;
  sector_id?: string | null;
  analysts: ReportAnalystInput[];
  changed_by: string;
  word_file_path?: string | null;
  model_file_path?: string | null;
};

export type ListReportsParams = {
  page: number;
  query: string | null;
  status: ReportStatus | null;
};

type AnalystRelation = NonNullable<ReportAnalyst["analyst"]>;

type ReportAnalystRow = {
  id: string;
  report_id: string;
  analyst_id: string;
  role: number;
  sort_order: number;
  created_at: string;
  updated_at: string;
  analyst?: AnalystRelation | AnalystRelation[] | null;
};

type ReportSummaryRow = Omit<ReportSummary, "analysts"> & {
  analysts?: ReportAnalystRow[] | null;
};

function firstRelation<T>(value: unknown): T | null {
  if (Array.isArray(value)) {
    return (value[0] as T | undefined) ?? null;
  }
  return (value as T | null) ?? null;
}

function normalizeReportAnalystRow(row: ReportAnalystRow): ReportAnalyst {
  return {
    id: row.id,
    report_id: row.report_id,
    analyst_id: row.analyst_id,
    role: row.role,
    sort_order: row.sort_order,
    created_at: row.created_at,
    updated_at: row.updated_at,
    analyst: firstRelation<ReportAnalyst["analyst"]>(row.analyst) ?? undefined,
  };
}

function normalizeReportSummaryRow(row: ReportSummaryRow): ReportSummary {
  return {
    id: row.id,
    owner_user_id: row.owner_user_id,
    title: row.title,
    report_type: row.report_type,
    status: row.status,
    current_version_no: row.current_version_no,
    coverage_id: row.coverage_id,
    sector_id: row.sector_id,
    published_by: row.published_by,
    published_at: row.published_at,
    created_at: row.created_at,
    updated_at: row.updated_at,
    analysts: Array.isArray(row.analysts)
      ? row.analysts.map((item) => normalizeReportAnalystRow(item))
      : [],
  };
}

async function listReportAnalysts(reportId: string): Promise<ReportAnalyst[]> {
  const supabase = await createServerClient();

  const { data, error } = await supabase
    .from("report_analyst")
    .select(
      `
      id,
      report_id,
      analyst_id,
      role,
      sort_order,
      created_at,
      updated_at,
      analyst:analyst_id (
        id,
        full_name,
        chinese_name,
        email
      )
    `,
    )
    .eq("report_id", reportId)
    .order("sort_order", { ascending: true });

  if (error || !data) {
    return [];
  }

  return (data as ReportAnalystRow[]).map((item) =>
    normalizeReportAnalystRow(item),
  );
}

export const toUtcTimestamp = toUtcTimestampValue;
export const getFileExtension = getFileExtensionValue;

export function validateUploadExtension(
  label: ReportFileLabel,
  fileName: string,
): Result<string> {
  const result = validateUploadExtensionValue(label, fileName);
  if (!result.ok) {
    return err(result.error);
  }
  return ok(result.extension);
}

export function buildReportStoragePath(params: {
  reportId: string;
  versionNo: number;
  label: ReportFileLabel;
  extension: string;
  ts?: Date;
}): string {
  return buildReportStoragePathValue(params);
}

function buildSnapshot(params: {
  report: {
    id: string;
    owner_user_id: string;
    title: string;
    report_type: ReportType;
    status: ReportStatus;
    current_version_no: number;
    coverage_id: string | null;
    sector_id: string | null;
  };
  analysts: ReportAnalyst[];
}): Record<string, unknown> {
  return {
    report_id: params.report.id,
    owner_user_id: params.report.owner_user_id,
    owner_name: params.report.owner_user_id,
    title: params.report.title,
    report_type: params.report.report_type,
    status: params.report.status,
    version_no: params.report.current_version_no,
    coverage_id: params.report.coverage_id,
    sector_id: params.report.sector_id,
    analyst_names: params.analysts.map((item) => item.analyst?.full_name ?? "Unknown"),
    analysts: params.analysts.map((item) => ({
      analyst_id: item.analyst_id,
      analyst_name: item.analyst?.full_name ?? "Unknown",
      role: item.role,
      sort_order: item.sort_order,
    })),
  };
}

export async function listReports(
  params: ListReportsParams,
): Promise<Result<PaginatedList<ReportSummary>>> {
  const supabase = await createServerClient();

  let queryBuilder = supabase.from("report").select(
    `
      id,
      owner_user_id,
      title,
      report_type,
      status,
      current_version_no,
      coverage_id,
      sector_id,
      published_by,
      published_at,
      created_at,
      updated_at,
      analysts:report_analyst (
        id,
        report_id,
        analyst_id,
        role,
        sort_order,
        created_at,
        updated_at,
        analyst:analyst_id (
          id,
          full_name,
          chinese_name,
          email
        )
      )
    `,
    { count: "exact" },
  );

  if (params.query) {
    const term = `%${params.query}%`;
    queryBuilder = queryBuilder.ilike("title", term);
  }

  if (params.status) {
    queryBuilder = queryBuilder.eq("status", params.status);
  }

  const from = (params.page - 1) * PAGE_SIZE;
  const to = from + PAGE_SIZE - 1;

  const { data, error, count } = await queryBuilder
    .order("updated_at", { ascending: false })
    .range(from, to);

  if (error) {
    return err(error.message);
  }

  const total = count ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const rows = (data ?? []) as ReportSummaryRow[];

  return ok({
    items: rows.map((item) =>
      normalizeReportSummaryRow(item),
    ),
    total,
    page: params.page,
    totalPages,
  });
}

export async function getReportDetail(reportId: string): Promise<Result<ReportDetail>> {
  const supabase = await createServerClient();

  const { data: reportData, error: reportError } = await supabase
    .from("report")
    .select(
      `
      id,
      owner_user_id,
      title,
      report_type,
      status,
      current_version_no,
      coverage_id,
      sector_id,
      published_by,
      published_at,
      created_at,
      updated_at,
      coverage:coverage_id (
        id,
        ticker,
        english_full_name
      ),
      sector:sector_id (
        id,
        name_en,
        name_cn
      ),
      analysts:report_analyst (
        id,
        report_id,
        analyst_id,
        role,
        sort_order,
        created_at,
        updated_at,
        analyst:analyst_id (
          id,
          full_name,
          chinese_name,
          email
        )
      )
    `,
    )
    .eq("id", reportId)
    .single();

  if (reportError || !reportData) {
    return err("Report not found or no permission.");
  }

  const { data: versions, error: versionError } = await supabase
    .from("report_version")
    .select("*")
    .eq("report_id", reportId)
    .order("version_no", { ascending: false });

  if (versionError) {
    return err(versionError.message);
  }

  const { data: logs, error: logError } = await supabase
    .from("report_status_log")
    .select("*")
    .eq("report_id", reportId)
    .order("action_at", { ascending: false });

  if (logError) {
    return err(logError.message);
  }

  const summary = normalizeReportSummaryRow(reportData as unknown as ReportSummaryRow);
  const detail: ReportDetail = {
    ...summary,
    coverage: firstRelation<ReportDetail["coverage"]>(reportData.coverage) ?? null,
    sector: firstRelation<ReportDetail["sector"]>(reportData.sector) ?? null,
    versions: (versions ?? []) as ReportVersion[],
    latest_version: ((versions ?? [])[0] as ReportVersion | undefined) ?? null,
    status_logs: (logs ?? []) as ReportStatusLog[],
  };

  return ok(detail);
}

export async function createReport(params: CreateReportParams): Promise<Result<ReportDetail>> {
  const supabase = await createServerClient();

  const { data: reportData, error: reportError } = await supabase
    .from("report")
    .insert({
      owner_user_id: params.owner_user_id,
      title: params.title,
      report_type: params.report_type,
      status: "draft",
      current_version_no: 0,
      coverage_id: params.coverage_id ?? null,
      sector_id: params.sector_id ?? null,
    })
    .select("id")
    .single();

  if (reportError || !reportData) {
    return err(reportError?.message ?? "Failed to create report.");
  }

  if (params.analysts.length > 0) {
    const { error: analystError } = await supabase.from("report_analyst").insert(
      params.analysts.map((item) => ({
        report_id: reportData.id,
        analyst_id: item.analyst_id,
        role: item.role,
        sort_order: item.sort_order,
      })),
    );

    if (analystError) {
      return err(analystError.message);
    }
  }

  return getReportDetail(reportData.id);
}

export async function replaceReportAnalysts(
  reportId: string,
  analysts: ReportAnalystInput[],
): Promise<Result<null>> {
  const supabase = await createServerClient();

  const { error: deleteError } = await supabase
    .from("report_analyst")
    .delete()
    .eq("report_id", reportId);

  if (deleteError) {
    return err(deleteError.message);
  }

  if (analysts.length > 0) {
    const { error: insertError } = await supabase.from("report_analyst").insert(
      analysts.map((item) => ({
        report_id: reportId,
        analyst_id: item.analyst_id,
        role: item.role,
        sort_order: item.sort_order,
      })),
    );

    if (insertError) {
      return err(insertError.message);
    }
  }

  return ok(null);
}

export async function saveReportContent(
  params: SaveReportContentParams,
): Promise<Result<ReportDetail>> {
  const supabase = await createServerClient();

  const { data: currentReport, error: currentError } = await supabase
    .from("report")
    .select(
      "id, owner_user_id, title, report_type, status, current_version_no, coverage_id, sector_id",
    )
    .eq("id", params.report_id)
    .single();

  if (currentError || !currentReport) {
    return err("Report not found or no permission.");
  }

  const nextVersionNo = (currentReport.current_version_no ?? 0) + 1;

  const { data: updatedReport, error: updateError } = await supabase
    .from("report")
    .update({
      title: params.title,
      report_type: params.report_type,
      coverage_id: params.coverage_id ?? null,
      sector_id: params.sector_id ?? null,
      current_version_no: nextVersionNo,
    })
    .eq("id", params.report_id)
    .select(
      "id, owner_user_id, title, report_type, status, current_version_no, coverage_id, sector_id",
    )
    .single();

  if (updateError || !updatedReport) {
    return err(updateError?.message ?? "Failed to update report.");
  }

  const replaceResult = await replaceReportAnalysts(params.report_id, params.analysts);
  if (!replaceResult.ok) {
    return replaceResult;
  }

  const currentAnalysts = await listReportAnalysts(params.report_id);
  const snapshotJson = buildSnapshot({
    report: updatedReport as {
      id: string;
      owner_user_id: string;
      title: string;
      report_type: ReportType;
      status: ReportStatus;
      current_version_no: number;
      coverage_id: string | null;
      sector_id: string | null;
    },
    analysts: currentAnalysts,
  });

  const { error: versionError } = await supabase.from("report_version").insert({
    report_id: params.report_id,
    version_no: nextVersionNo,
    snapshot_json: snapshotJson,
    word_file_path: params.word_file_path ?? null,
    model_file_path: params.model_file_path ?? null,
    changed_by: params.changed_by,
    changed_at: new Date().toISOString(),
  });

  if (versionError) {
    return err(versionError.message);
  }

  return getReportDetail(params.report_id);
}

export async function changeReportStatus(params: {
  report_id: string;
  to_status: ReportStatus;
  action_by: string;
  reason?: string | null;
}): Promise<Result<ReportDetail>> {
  const supabase = await createServerClient();

  const { data: currentReport, error: currentError } = await supabase
    .from("report")
    .select("id, status, current_version_no")
    .eq("id", params.report_id)
    .single();

  if (currentError || !currentReport) {
    return err("Report not found or no permission.");
  }

  const updatePayload: Record<string, unknown> = {
    status: params.to_status,
  };

  if (params.to_status === "published") {
    updatePayload.published_by = params.action_by;
    updatePayload.published_at = new Date().toISOString();
  }

  const { error: updateError } = await supabase
    .from("report")
    .update(updatePayload)
    .eq("id", params.report_id);

  if (updateError) {
    return err(updateError.message);
  }

  const { error: logError } = await supabase.from("report_status_log").insert({
    report_id: params.report_id,
    from_status: currentReport.status,
    to_status: params.to_status,
    action_by: params.action_by,
    action_at: new Date().toISOString(),
    reason: params.reason?.trim() || null,
    version_no: currentReport.current_version_no,
  });

  if (logError) {
    return err(logError.message);
  }

  return getReportDetail(params.report_id);
}

export async function getReportDownloadUrl(params: {
  report_id: string;
  file_path: string;
}): Promise<Result<string>> {
  const supabase = await createServerClient();

  const { data: reportVersionByWord } = await supabase
    .from("report_version")
    .select("id")
    .eq("report_id", params.report_id)
    .eq("word_file_path", params.file_path)
    .maybeSingle();

  const { data: reportVersionByModel } = reportVersionByWord
    ? { data: null }
    : await supabase
        .from("report_version")
        .select("id")
        .eq("report_id", params.report_id)
        .eq("model_file_path", params.file_path)
        .maybeSingle();

  if (!reportVersionByWord && !reportVersionByModel) {
    return err("No permission to download this file.");
  }

  const { data, error } = await supabase.storage
    .from("reports")
    .createSignedUrl(params.file_path, 60 * 5);

  if (error || !data?.signedUrl) {
    return err(error?.message ?? "Failed to create download URL.");
  }

  return ok(data.signedUrl);
}
