import "server-only";

import type { Result } from "@/lib/result";

import {
  changeReportStatus,
  getReportDetail,
  listReports,
  type ReportDetail,
  type ReportSummary,
} from "@/features/reports/repo/reports-repo";

export async function listReviewReports(params: {
  page: number;
  query: string | null;
  status: "submitted" | "published" | "rejected";
}): Promise<
  Result<{
    items: ReportSummary[];
    total: number;
    page: number;
    totalPages: number;
  }>
> {
  return listReports({
    page: params.page,
    query: params.query,
    status: params.status,
  });
}

export async function getReviewReportDetail(
  reportId: string,
): Promise<Result<ReportDetail>> {
  return getReportDetail(reportId);
}

export async function approveReport(params: {
  report_id: string;
  action_by: string;
}): Promise<Result<ReportDetail>> {
  return changeReportStatus({
    report_id: params.report_id,
    to_status: "published",
    action_by: params.action_by,
  });
}

export async function rejectReport(params: {
  report_id: string;
  action_by: string;
  reason: string;
}): Promise<Result<ReportDetail>> {
  return changeReportStatus({
    report_id: params.report_id,
    to_status: "rejected",
    action_by: params.action_by,
    reason: params.reason,
  });
}

export async function reopenReport(params: {
  report_id: string;
  action_by: string;
}): Promise<Result<ReportDetail>> {
  return changeReportStatus({
    report_id: params.report_id,
    to_status: "draft",
    action_by: params.action_by,
  });
}
