"use server";

import { revalidatePath } from "next/cache";

import {
  reportCreateSchema,
  reportDirectSubmitSchema,
  reportDownloadSchema,
  reportSaveSchema,
  reportSubmitSchema,
  type ReportStatus,
} from "@/domain/schemas/report";
import { listAllActiveAnalysts } from "@/features/analyst-info/repo/analysts-repo";
import { err, type Result } from "@/lib/result";
import { requireAuth } from "@/lib/supabase/server";

import {
  changeReportStatus,
  createReport,
  getReportDetail,
  getReportDownloadUrl,
  listReports,
  saveReportContent,
  type ReportDetail,
} from "./repo/reports-repo";

type Role = "admin" | "sa" | "analyst";

async function getActor(): Promise<
  Result<{ user: Awaited<ReturnType<typeof requireAuth>>; role: Role }>
> {
  try {
    const user = await requireAuth();
    const role = user.app_metadata?.role as Role | undefined;
    if (role !== "admin" && role !== "sa" && role !== "analyst") {
      return err("No permission");
    }
    return { ok: true, data: { user, role } };
  } catch {
    return err("Unauthorized");
  }
}

function canCreateOrEdit(role: Role): boolean {
  return role === "admin" || role === "analyst";
}

function isEditableStatus(status: ReportStatus): boolean {
  return status === "draft" || status === "submitted";
}

async function validateAnalysts(input: { analyst_id: string }[]): Promise<string | null> {
  if (input.length === 0) {
    return null;
  }

  const analystsResult = await listAllActiveAnalysts();
  if (!analystsResult.ok) {
    return "Failed to validate analyst list.";
  }

  const activeIds = new Set(analystsResult.data.map((item) => item.id));
  const hasInvalid = input.some((item) => !activeIds.has(item.analyst_id));
  if (hasInvalid) {
    return "Analyst must be selected from the active analyst list.";
  }

  return null;
}

async function assertEditable(
  role: Role,
  userId: string,
  reportId: string,
): Promise<Result<ReportDetail>> {
  const detailResult = await getReportDetail(reportId);
  if (!detailResult.ok) {
    return detailResult;
  }

  const detail = detailResult.data;
  if (!isEditableStatus(detail.status)) {
    return err("Only draft/submitted reports can be edited.");
  }

  if (role === "analyst" && detail.owner_user_id !== userId) {
    return err("No permission");
  }

  return detailResult;
}

export async function listReportsAction(input: {
  page?: number;
  query?: string | null;
  status?: ReportStatus | null;
}): Promise<
  Result<{
    items: Awaited<ReturnType<typeof listReports>> extends Result<infer T>
      ? T extends { items: infer U }
        ? U
        : never
      : never;
    total: number;
    page: number;
    totalPages: number;
    applied_status: ReportStatus | null;
  }>
> {
  const actor = await getActor();
  if (!actor.ok) {
    return actor;
  }

  const { role } = actor.data;
  const page = Math.max(1, input.page ?? 1);
  const query = input.query ?? null;
  const appliedStatus =
    input.status ?? (role === "admin" || role === "sa" ? "submitted" : null);

  const listResult = await listReports({
    page,
    query,
    status: appliedStatus,
  });

  if (!listResult.ok) {
    return listResult;
  }

  return {
    ok: true,
    data: {
      ...listResult.data,
      applied_status: appliedStatus,
    },
  };
}

export async function getReportDetailAction(reportId: string): Promise<Result<ReportDetail>> {
  const actor = await getActor();
  if (!actor.ok) {
    return actor;
  }
  return getReportDetail(reportId);
}

export async function createReportAction(input: unknown): Promise<Result<ReportDetail>> {
  const actor = await getActor();
  if (!actor.ok) {
    return actor;
  }

  const { role, user } = actor.data;
  if (!canCreateOrEdit(role)) {
    return err("No permission");
  }

  const parsed = reportCreateSchema.safeParse(input);
  if (!parsed.success) {
    return err(parsed.error.issues[0]?.message ?? "Invalid input.");
  }

  const analystError = await validateAnalysts(parsed.data.analysts);
  if (analystError) {
    return err(analystError);
  }

  const createResult = await createReport({
    owner_user_id: user.id,
    title: parsed.data.title,
    report_type: parsed.data.report_type,
    coverage_id: parsed.data.coverage_id ?? null,
    sector_id: parsed.data.sector_id ?? null,
    analysts: parsed.data.analysts,
  });

  if (createResult.ok) {
    revalidatePath("/reports");
    revalidatePath("/report-review");
  }

  return createResult;
}

export async function saveReportContentAction(input: unknown): Promise<Result<ReportDetail>> {
  const actor = await getActor();
  if (!actor.ok) {
    return actor;
  }

  const { role, user } = actor.data;
  if (!canCreateOrEdit(role)) {
    return err("No permission");
  }

  const parsed = reportSaveSchema.safeParse(input);
  if (!parsed.success) {
    return err(parsed.error.issues[0]?.message ?? "Invalid input.");
  }

  const editableResult = await assertEditable(role, user.id, parsed.data.report_id);
  if (!editableResult.ok) {
    return editableResult;
  }

  const analystError = await validateAnalysts(parsed.data.analysts);
  if (analystError) {
    return err(analystError);
  }

  const saveResult = await saveReportContent({
    ...parsed.data,
    changed_by: user.id,
  });

  if (saveResult.ok) {
    revalidatePath("/reports");
    revalidatePath("/report-review");
  }

  return saveResult;
}

export async function submitReportAction(input: unknown): Promise<Result<ReportDetail>> {
  const actor = await getActor();
  if (!actor.ok) {
    return actor;
  }

  const { role, user } = actor.data;
  if (!canCreateOrEdit(role)) {
    return err("No permission");
  }

  const parsed = reportSubmitSchema.safeParse(input);
  if (!parsed.success) {
    return err(parsed.error.issues[0]?.message ?? "Invalid input.");
  }

  const detailResult = await getReportDetail(parsed.data.report_id);
  if (!detailResult.ok) {
    return detailResult;
  }

  const detail = detailResult.data;
  if (detail.status !== "draft") {
    return err("Only draft reports can be submitted.");
  }

  if (role === "analyst" && detail.owner_user_id !== user.id) {
    return err("No permission");
  }

  const submitResult = await changeReportStatus({
    report_id: parsed.data.report_id,
    to_status: "submitted",
    action_by: user.id,
  });

  if (submitResult.ok) {
    revalidatePath("/reports");
    revalidatePath("/report-review");
  }

  return submitResult;
}

export async function directSubmitReportAction(input: unknown): Promise<Result<ReportDetail>> {
  const actor = await getActor();
  if (!actor.ok) {
    return actor;
  }

  const { role, user } = actor.data;
  if (!canCreateOrEdit(role)) {
    return err("No permission");
  }

  const parsed = reportDirectSubmitSchema.safeParse(input);
  if (!parsed.success) {
    return err(parsed.error.issues[0]?.message ?? "Invalid input.");
  }

  const analystError = await validateAnalysts(parsed.data.analysts);
  if (analystError) {
    return err(analystError);
  }

  let reportId = parsed.data.report_id;

  if (!reportId) {
    const createResult = await createReport({
      owner_user_id: user.id,
      title: parsed.data.title,
      report_type: parsed.data.report_type,
      coverage_id: parsed.data.coverage_id ?? null,
      sector_id: parsed.data.sector_id ?? null,
      analysts: parsed.data.analysts,
    });

    if (!createResult.ok) {
      return createResult;
    }

    reportId = createResult.data.id;
  }

  const editableResult = await assertEditable(role, user.id, reportId);
  if (!editableResult.ok) {
    return editableResult;
  }

  if (editableResult.data.status !== "draft") {
    return err("Direct submit only supports draft reports.");
  }

  const saveResult = await saveReportContent({
    report_id: reportId,
    title: parsed.data.title,
    report_type: parsed.data.report_type,
    coverage_id: parsed.data.coverage_id ?? null,
    sector_id: parsed.data.sector_id ?? null,
    analysts: parsed.data.analysts,
    changed_by: user.id,
    word_file_path: parsed.data.word_file_path ?? null,
    model_file_path: parsed.data.model_file_path ?? null,
  });

  if (!saveResult.ok) {
    return saveResult;
  }

  const submitResult = await changeReportStatus({
    report_id: reportId,
    to_status: "submitted",
    action_by: user.id,
  });

  if (!submitResult.ok) {
    return err("已保存为 Draft，提交失败");
  }

  revalidatePath("/reports");
  revalidatePath("/report-review");
  return submitResult;
}

export async function getReportDownloadUrlAction(
  input: unknown,
): Promise<Result<string>> {
  const actor = await getActor();
  if (!actor.ok) {
    return actor;
  }

  const parsed = reportDownloadSchema.safeParse(input);
  if (!parsed.success) {
    return err(parsed.error.issues[0]?.message ?? "Invalid input.");
  }

  return getReportDownloadUrl(parsed.data);
}
