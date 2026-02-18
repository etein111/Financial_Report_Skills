"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { ActionButton } from "@/components/ui/action-button";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FileDropzone } from "@/components/ui/file-dropzone";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/select";
import { Table, TD, TH, THead, TR } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import type {
  ReportAnalystInput,
  ReportStatus,
  ReportType,
} from "@/domain/schemas/report";
import type { Analyst } from "@/features/analyst-info/repo/analysts-repo";
import {
  createReportAction,
  directSubmitReportAction,
  getReportDetailAction,
  getReportDownloadUrlAction,
  saveReportContentAction,
  submitReportAction,
} from "@/features/reports/actions";
import {
  buildReportStoragePath,
  validateUploadExtension,
} from "@/features/reports/file-utils";
import type {
  ReportDetail,
  ReportSummary,
} from "@/features/reports/repo/reports-repo";
import { createBrowserClient } from "@/lib/supabase/browser";

export interface ReportsPageClientProps {
  reports: ReportSummary[];
  total: number;
  page: number;
  totalPages: number;
  currentQuery: string | null;
  currentStatus: ReportStatus | null;
  userRole: "admin" | "sa" | "analyst";
  currentUserId: string;
  analysts: Analyst[];
}

type FormAnalyst = ReportAnalystInput;

const REPORT_TYPE_OPTIONS: { value: ReportType; label: string }[] = [
  { value: "company", label: "Company" },
  { value: "sector", label: "Sector" },
  { value: "company_flash", label: "Company Flash" },
  { value: "sector_flash", label: "Sector Flash" },
  { value: "common", label: "Common" },
];

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: "all", label: "All" },
  { value: "draft", label: "Draft" },
  { value: "submitted", label: "Submitted" },
  { value: "published", label: "Published" },
  { value: "rejected", label: "Rejected" },
];

function statusTone(
  status: ReportStatus,
): "secondary" | "blue" | "green" | "red" {
  if (status === "draft") return "secondary";
  if (status === "submitted") return "blue";
  if (status === "published") return "green";
  return "red";
}

function toQueryString(params: { q: string; status: string; page: number }) {
  const sp = new URLSearchParams();
  if (params.q.trim()) {
    sp.set("query", params.q.trim());
  }
  if (params.status && params.status !== "all") {
    sp.set("status", params.status);
  }
  if (params.page > 1) {
    sp.set("page", String(params.page));
  }
  const value = sp.toString();
  return value ? `?${value}` : "";
}

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) {
    return iso;
  }
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(d);
}

export function ReportsPageClient({
  reports,
  total,
  page,
  totalPages,
  currentQuery,
  currentStatus,
  userRole,
  currentUserId,
  analysts,
}: ReportsPageClientProps) {
  const router = useRouter();
  const toast = useToast();

  const canCreate = userRole === "admin" || userRole === "analyst";
  const [queryDraft, setQueryDraft] = React.useState(currentQuery ?? "");
  // Use currentStatus from server, or default based on role
  // admin/sa default to "submitted", others default to null (meaning "all")
  const defaultStatus =
    userRole === "admin" || userRole === "sa" ? "submitted" : null;
  const [statusFilter, setStatusFilter] = React.useState<string | null>(
    currentStatus ?? defaultStatus,
  );

  React.useEffect(() => {
    setQueryDraft(currentQuery ?? "");
    const newDefaultStatus =
      userRole === "admin" || userRole === "sa" ? "submitted" : null;
    setStatusFilter(currentStatus ?? newDefaultStatus);
  }, [currentQuery, currentStatus, userRole]);

  const [formOpen, setFormOpen] = React.useState(false);
  const [loadingDetail, setLoadingDetail] = React.useState(false);
  const [activeReport, setActiveReport] = React.useState<ReportDetail | null>(
    null,
  );

  const [formTitle, setFormTitle] = React.useState("");
  const [formReportType, setFormReportType] =
    React.useState<ReportType>("company");
  const [formAnalysts, setFormAnalysts] = React.useState<FormAnalyst[]>([]);
  const [formErrors, setFormErrors] = React.useState<Record<string, string>>(
    {},
  );

  const [reportFile, setReportFile] = React.useState<File | null>(null);
  const [modelFile, setModelFile] = React.useState<File | null>(null);
  const [saving, setSaving] = React.useState(false);

  function goToPage(nextPage: number) {
    router.push(
      `/reports${toQueryString({ q: queryDraft, status: statusFilter || "all", page: nextPage })}`,
    );
  }

  function submitSearch(e: React.FormEvent) {
    e.preventDefault();
    goToPage(1);
  }

  function onStatusChange(value: string) {
    setStatusFilter(value as ReportStatus | "all");
    router.push(
      `/reports${toQueryString({ q: queryDraft, status: value, page: 1 })}`,
    );
  }

  async function openDetail(reportId: string) {
    setFormOpen(true);
    setLoadingDetail(true);
    setFormErrors({});

    const detailResult = await getReportDetailAction(reportId);
    setLoadingDetail(false);

    if (!detailResult.ok) {
      toast.error(detailResult.error, { title: "Error" });
      setFormOpen(false);
      return;
    }

    const detail = detailResult.data;
    setActiveReport(detail);
    setFormTitle(detail.title);
    setFormReportType(detail.report_type);
    setFormAnalysts(
      detail.analysts
        .sort((a, b) => a.sort_order - b.sort_order)
        .map((item) => ({
          analyst_id: item.analyst_id,
          role: item.role,
          sort_order: item.sort_order,
        })),
    );
    setReportFile(null);
    setModelFile(null);
  }

  function canEditReport(
    report: Pick<ReportSummary, "owner_user_id" | "status">,
  ): boolean {
    if (userRole === "admin") {
      return report.status === "draft" || report.status === "submitted";
    }
    if (userRole === "analyst") {
      return (
        report.owner_user_id === currentUserId &&
        (report.status === "draft" || report.status === "submitted")
      );
    }
    return false;
  }

  function canSubmitReport(
    report: Pick<ReportSummary, "owner_user_id" | "status">,
  ): boolean {
    if (report.status !== "draft") {
      return false;
    }
    if (userRole === "admin") {
      return true;
    }
    if (userRole === "analyst") {
      return report.owner_user_id === currentUserId;
    }
    return false;
  }

  function addAnalyst() {
    if (formAnalysts.length >= 4) {
      return;
    }

    setFormAnalysts((prev) => [
      ...prev,
      {
        analyst_id: "",
        role: prev.length + 1,
        sort_order: prev.length + 1,
      },
    ]);
  }

  function removeAnalyst(index: number) {
    setFormAnalysts((prev) =>
      prev
        .filter((_, idx) => idx !== index)
        .map((item, idx) => ({
          ...item,
          role: idx + 1,
          sort_order: idx + 1,
        })),
    );
  }

  function updateAnalyst(
    index: number,
    field: keyof FormAnalyst,
    value: string | number,
  ) {
    setFormAnalysts((prev) => {
      const next = [...prev];
      next[index] = {
        ...next[index],
        [field]: value,
      };
      return next;
    });
  }

  function getAnalystOptions(
    index: number,
  ): { value: string; label: string }[] {
    const selectedOthers = new Set(
      formAnalysts
        .filter((_, idx) => idx !== index)
        .map((item) => item.analyst_id)
        .filter(Boolean),
    );
    const current = formAnalysts[index]?.analyst_id;

    return [
      { value: "", label: "Select analyst..." },
      ...analysts
        .filter((item) => item.id === current || !selectedOthers.has(item.id))
        .map((item) => ({ value: item.id, label: item.full_name })),
    ];
  }

  function buildValidatedAnalysts(): FormAnalyst[] {
    const selected = formAnalysts.filter((item) => item.analyst_id);
    return selected.map((item, index) => ({
      analyst_id: item.analyst_id,
      role: index + 1,
      sort_order: index + 1,
    }));
  }

  function validateForm(): FormAnalyst[] | null {
    const next: Record<string, string> = {};
    if (!formTitle.trim()) {
      next.title = "Title is required";
    }

    const selected = buildValidatedAnalysts();
    const unique = new Set(selected.map((item) => item.analyst_id));
    if (unique.size !== selected.length) {
      next.analysts = "Analysts must be unique";
    }

    setFormErrors(next);
    if (Object.keys(next).length > 0) {
      return null;
    }

    return selected;
  }

  async function uploadReportFiles(params: {
    reportId: string;
    versionNo: number;
  }): Promise<
    Result<{ word_file_path: string | null; model_file_path: string | null }>
  > {
    const supabase = createBrowserClient();

    let wordFilePath: string | null =
      activeReport?.latest_version?.word_file_path ?? null;
    let modelFilePath: string | null =
      activeReport?.latest_version?.model_file_path ?? null;

    if (reportFile) {
      const check = validateUploadExtension("report", reportFile.name);
      if (!check.ok) {
        return { ok: false, error: check.error };
      }
      const path = buildReportStoragePath({
        reportId: params.reportId,
        versionNo: params.versionNo,
        label: "report",
        extension: check.extension,
      });
      const { error } = await supabase.storage
        .from("reports")
        .upload(path, reportFile, {
          upsert: true,
        });
      if (error) {
        return { ok: false, error: error.message };
      }
      wordFilePath = path;
    }

    if (modelFile) {
      const check = validateUploadExtension("model", modelFile.name);
      if (!check.ok) {
        return { ok: false, error: check.error };
      }
      const path = buildReportStoragePath({
        reportId: params.reportId,
        versionNo: params.versionNo,
        label: "model",
        extension: check.extension,
      });
      const { error } = await supabase.storage
        .from("reports")
        .upload(path, modelFile, {
          upsert: true,
        });
      if (error) {
        return { ok: false, error: error.message };
      }
      modelFilePath = path;
    }

    return {
      ok: true,
      data: {
        word_file_path: wordFilePath,
        model_file_path: modelFilePath,
      },
    };
  }

  async function handleSaveDraft() {
    const analystsValue = validateForm();
    if (!analystsValue) {
      return;
    }

    setSaving(true);

    try {
      let reportId = activeReport?.id;
      let baseVersionNo = activeReport?.current_version_no ?? 0;

      if (!reportId) {
        const createResult = await createReportAction({
          title: formTitle.trim(),
          report_type: formReportType,
          analysts: analystsValue,
        });
        if (!createResult.ok) {
          toast.error(createResult.error, { title: "Error" });
          return;
        }
        reportId = createResult.data.id;
        baseVersionNo = createResult.data.current_version_no;
      }

      const uploadResult = await uploadReportFiles({
        reportId,
        versionNo: baseVersionNo + 1,
      });

      if (!uploadResult.ok) {
        toast.error(uploadResult.error, { title: "Error" });
        return;
      }

      const saveResult = await saveReportContentAction({
        report_id: reportId,
        title: formTitle.trim(),
        report_type: formReportType,
        analysts: analystsValue,
        word_file_path: uploadResult.data.word_file_path,
        model_file_path: uploadResult.data.model_file_path,
      });

      if (!saveResult.ok) {
        toast.error(saveResult.error, { title: "Error" });
        return;
      }

      setActiveReport(saveResult.data);
      setReportFile(null);
      setModelFile(null);
      toast.success("Draft saved.", { title: "Success" });
      router.refresh();
    } finally {
      setSaving(false);
    }
  }

  async function handleSubmit() {
    if (!activeReport) {
      toast.error("Please save draft first.", { title: "Error" });
      return;
    }

    setSaving(true);
    try {
      const submitResult = await submitReportAction({
        report_id: activeReport.id,
      });
      if (!submitResult.ok) {
        toast.error(submitResult.error, { title: "Error" });
        return;
      }

      setActiveReport(submitResult.data);
      toast.success("Report submitted.", { title: "Success" });
      router.refresh();
    } finally {
      setSaving(false);
    }
  }

  async function handleDirectSubmit() {
    const analystsValue = validateForm();
    if (!analystsValue) {
      return;
    }

    setSaving(true);
    try {
      let reportId = activeReport?.id;
      let baseVersionNo = activeReport?.current_version_no ?? 0;

      if (!reportId) {
        const createResult = await createReportAction({
          title: formTitle.trim(),
          report_type: formReportType,
          analysts: analystsValue,
        });
        if (!createResult.ok) {
          toast.error(createResult.error, { title: "Error" });
          return;
        }
        reportId = createResult.data.id;
        baseVersionNo = createResult.data.current_version_no;
      }

      const uploadResult = await uploadReportFiles({
        reportId,
        versionNo: baseVersionNo + 1,
      });
      if (!uploadResult.ok) {
        toast.error(uploadResult.error, { title: "Error" });
        return;
      }

      const directResult = await directSubmitReportAction({
        report_id: reportId,
        title: formTitle.trim(),
        report_type: formReportType,
        analysts: analystsValue,
        word_file_path: uploadResult.data.word_file_path,
        model_file_path: uploadResult.data.model_file_path,
      });

      if (!directResult.ok) {
        toast.error(directResult.error, { title: "Error" });
        return;
      }

      setActiveReport(directResult.data);
      setReportFile(null);
      setModelFile(null);
      toast.success("Report submitted.", { title: "Success" });
      router.refresh();
    } finally {
      setSaving(false);
    }
  }

  async function handleDownload(filePath: string) {
    if (!activeReport) {
      return;
    }

    const result = await getReportDownloadUrlAction({
      report_id: activeReport.id,
      file_path: filePath,
    });

    if (!result.ok) {
      toast.error(result.error, { title: "Error" });
      return;
    }

    window.open(result.data, "_blank", "noopener,noreferrer");
  }

  function getVersionReason(versionNo: number): string | null {
    if (!activeReport) {
      return null;
    }
    const matched = activeReport.status_logs.find(
      (item) => item.version_no === versionNo && item.reason,
    );
    return matched?.reason ?? null;
  }

  const canEditActive = activeReport ? canEditReport(activeReport) : canCreate;
  const canDirectSubmit =
    canEditActive && (!activeReport || activeReport.status === "draft");
  const canSubmit = activeReport ? canSubmitReport(activeReport) : false;

  return (
    <div className="min-h-screen">
      <header className="border-b border-white/10 bg-zinc-900/60 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
          <div className="text-xl font-semibold text-zinc-50">Reports</div>
          {canCreate ? (
            <a
              href="/reports/new"
              className="inline-flex items-center justify-center rounded-[6px] bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors duration-200 hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/60"
            >
              Add Report
            </a>
          ) : (
            <div />
          )}
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-4 px-6 py-8">
        <div className="flex items-end justify-between gap-4">
          <form className="flex flex-1 gap-4" onSubmit={submitSearch}>
            <div className="w-full max-w-md">
              <Input
                label="Search"
                placeholder="Search by title"
                value={queryDraft}
                onChange={(event) => setQueryDraft(event.target.value)}
              />
            </div>
            <div className="w-56">
              <Select
                label="Status"
                value={statusFilter ?? "all"}
                onChange={(event) => onStatusChange(event.target.value)}
                options={STATUS_OPTIONS}
              />
            </div>
          </form>
        </div>

        <Table>
          <THead>
            <TR>
              <TH>Title</TH>
              <TH>Type</TH>
              <TH>Status</TH>
              <TH>Owner</TH>
              <TH>Updated</TH>
              <TH className="text-right">Actions</TH>
            </TR>
          </THead>
          <tbody>
            {reports.length === 0 ? (
              <TR>
                <TD colSpan={6} className="py-10 text-center text-zinc-400">
                  No reports found.
                </TD>
              </TR>
            ) : (
              reports.map((report) => (
                <TR key={report.id}>
                  <TD className="font-medium text-zinc-100">{report.title}</TD>
                  <TD className="text-zinc-300">{report.report_type}</TD>
                  <TD>
                    <Badge tone={statusTone(report.status)}>
                      {report.status}
                    </Badge>
                  </TD>
                  <TD className="text-zinc-300">
                    {report.owner_user_id === currentUserId
                      ? "Me"
                      : `${report.owner_user_id.slice(0, 8)}...`}
                  </TD>
                  <TD className="text-zinc-400">
                    {formatDateTime(report.updated_at)}
                  </TD>
                  <TD>
                    <div className="flex justify-end gap-2">
                      <ActionButton onClick={() => openDetail(report.id)}>
                        {canEditReport(report) ? "Edit" : "View"}
                      </ActionButton>
                    </div>
                  </TD>
                </TR>
              ))
            )}
          </tbody>
        </Table>

        <Pagination page={page} totalPages={totalPages} onChange={goToPage} />
      </main>

      <Modal
        open={formOpen}
        title={activeReport ? "Edit Report" : "Create Report"}
        onClose={() => setFormOpen(false)}
        className="max-w-3xl"
        footer={
          <>
            <Button
              variant="ghost"
              type="button"
              onClick={() => setFormOpen(false)}
            >
              Close
            </Button>
            {canEditActive ? (
              <Button
                type="button"
                variant="secondary"
                onClick={handleSaveDraft}
                isLoading={saving}
              >
                Save Draft
              </Button>
            ) : null}
            {canSubmit ? (
              <Button type="button" onClick={handleSubmit} isLoading={saving}>
                Submit
              </Button>
            ) : null}
            {canDirectSubmit ? (
              <Button
                type="button"
                onClick={handleDirectSubmit}
                isLoading={saving}
              >
                Direct Submit
              </Button>
            ) : null}
          </>
        }
      >
        {loadingDetail ? (
          <div className="py-8 text-center text-zinc-400">
            Loading report...
          </div>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <Input
                label="Title"
                value={formTitle}
                onChange={(event) => setFormTitle(event.target.value)}
                error={formErrors.title}
                disabled={!canEditActive}
              />
              <Select
                label="Report Type"
                value={formReportType}
                onChange={(event) =>
                  setFormReportType(event.target.value as ReportType)
                }
                options={REPORT_TYPE_OPTIONS}
                disabled={!canEditActive}
              />
            </div>

            <div className="space-y-2 rounded-[12px] border border-white/10 bg-zinc-900/70 p-4">
              <div className="flex items-center justify-between">
                <div className="text-sm font-medium text-zinc-200">
                  Analysts
                </div>
                {canEditActive ? (
                  <Button type="button" variant="ghost" onClick={addAnalyst}>
                    Add Analyst
                  </Button>
                ) : null}
              </div>
              {formAnalysts.length === 0 ? (
                <p className="text-sm text-zinc-500">No analyst assigned.</p>
              ) : (
                formAnalysts.map((item, index) => (
                  <div
                    key={`${item.analyst_id}-${index}`}
                    className="grid grid-cols-12 gap-2"
                  >
                    <div className="col-span-8">
                      <Select
                        value={item.analyst_id}
                        onChange={(event) =>
                          updateAnalyst(index, "analyst_id", event.target.value)
                        }
                        options={getAnalystOptions(index)}
                        disabled={!canEditActive}
                      />
                    </div>
                    <div className="col-span-2 flex items-center text-sm text-zinc-400">
                      #{index + 1}
                    </div>
                    <div className="col-span-2">
                      {canEditActive ? (
                        <Button
                          type="button"
                          variant="ghost"
                          className="w-full"
                          onClick={() => removeAnalyst(index)}
                        >
                          Remove
                        </Button>
                      ) : null}
                    </div>
                  </div>
                ))
              )}
              {formErrors.analysts ? (
                <p className="text-xs text-red-500">{formErrors.analysts}</p>
              ) : null}
            </div>

            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <FileDropzone
                label="Report File"
                accept=".doc,.docx,.pdf"
                file={reportFile}
                onFileChange={setReportFile}
                disabled={!canEditActive}
                hint="Supports .doc/.docx/.pdf"
              />
              <FileDropzone
                label="Model File"
                accept=".xls,.xlsx,.csv"
                file={modelFile}
                onFileChange={setModelFile}
                disabled={!canEditActive}
                hint="Supports .xls/.xlsx/.csv"
              />
            </div>

            {activeReport ? (
              <div className="rounded-[12px] border border-white/10 bg-zinc-900/70 p-4">
                <div className="mb-2 text-sm font-medium text-zinc-200">
                  Files
                </div>
                <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                  <div className="rounded-[8px] border border-white/10 bg-zinc-800/40 p-3 text-sm text-zinc-300">
                    <div className="mb-1 text-xs text-zinc-500">Report</div>
                    {activeReport.latest_version?.word_file_path ? (
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() =>
                          handleDownload(
                            activeReport.latest_version!.word_file_path!,
                          )
                        }
                      >
                        Download
                      </Button>
                    ) : (
                      <span className="text-zinc-500">No file</span>
                    )}
                  </div>
                  <div className="rounded-[8px] border border-white/10 bg-zinc-800/40 p-3 text-sm text-zinc-300">
                    <div className="mb-1 text-xs text-zinc-500">Model</div>
                    {activeReport.latest_version?.model_file_path ? (
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() =>
                          handleDownload(
                            activeReport.latest_version!.model_file_path!,
                          )
                        }
                      >
                        Download
                      </Button>
                    ) : (
                      <span className="text-zinc-500">No file</span>
                    )}
                  </div>
                </div>
              </div>
            ) : null}

            {activeReport ? (
              <div className="space-y-2 rounded-[12px] border border-white/10 bg-zinc-900/70 p-4">
                <div className="text-sm font-medium text-zinc-200">
                  Report Version History
                </div>
                {activeReport.versions.length === 0 ? (
                  <p className="text-sm text-zinc-500">No versions yet.</p>
                ) : (
                  <div className="space-y-2">
                    {activeReport.versions.map((item) => (
                      <div
                        key={item.id}
                        className="rounded-[8px] border border-white/10 bg-zinc-800/40 p-3 text-sm"
                      >
                        <div className="flex items-center gap-2 text-zinc-200">
                          <Badge tone="zinc">v{item.version_no}</Badge>
                          <span>
                            Changed by {item.changed_by.slice(0, 8)}...
                          </span>
                        </div>
                        <div className="mt-1 text-xs text-zinc-500">
                          {formatDateTime(item.changed_at)}
                        </div>
                        {getVersionReason(item.version_no) ? (
                          <div className="mt-1 text-xs text-amber-300">
                            Note: {getVersionReason(item.version_no)}
                          </div>
                        ) : null}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : null}

            {activeReport ? (
              <div className="space-y-2 rounded-[12px] border border-white/10 bg-zinc-900/70 p-4">
                <div className="text-sm font-medium text-zinc-200">
                  Report Status History
                </div>
                {activeReport.status_logs.length === 0 ? (
                  <p className="text-sm text-zinc-500">No history yet.</p>
                ) : (
                  <div className="space-y-2">
                    {activeReport.status_logs.map((item) => (
                      <div
                        key={item.id}
                        className="rounded-[8px] border border-white/10 bg-zinc-800/40 p-3 text-sm"
                      >
                        <div className="flex items-center gap-2 text-zinc-200">
                          <span>{item.from_status}</span>
                          <span className="text-zinc-500">-&gt;</span>
                          <span>{item.to_status}</span>
                          <Badge tone="zinc">v{item.version_no}</Badge>
                        </div>
                        <div className="mt-1 text-xs text-zinc-500">
                          {formatDateTime(item.action_at)} by{" "}
                          {item.action_by_name ??
                            `${item.action_by.slice(0, 8)}...`}
                        </div>
                        {item.reason ? (
                          <div className="mt-1 text-xs text-amber-300">
                            Note: {item.reason}
                          </div>
                        ) : null}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : null}
          </div>
        )}
      </Modal>
    </div>
  );
}

type Result<T> = { ok: true; data: T } | { ok: false; error: string };
