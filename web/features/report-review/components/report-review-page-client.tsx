"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { ActionButton } from "@/components/ui/action-button";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/select";
import { Table, TD, TH, THead, TR } from "@/components/ui/table";
import { useToast } from "@/components/ui/toast";
import { getReportDownloadUrlAction } from "@/features/reports/actions";
import type { ReportDetail, ReportSummary } from "@/features/reports/repo/reports-repo";

import {
  executeReviewAction,
  getReviewReportDetailAction,
} from "../actions";

export interface ReportReviewPageClientProps {
  reports: ReportSummary[];
  total: number;
  page: number;
  totalPages: number;
  currentQuery: string | null;
  currentStatus: "submitted" | "published" | "rejected";
}

const FILTER_OPTIONS = [
  { value: "submitted", label: "Submitted" },
  { value: "published", label: "Published" },
  { value: "rejected", label: "Rejected" },
];

function statusTone(status: string): "blue" | "green" | "red" {
  if (status === "submitted") return "blue";
  if (status === "published") return "green";
  return "red";
}

function toQueryString(params: { q: string; status: string; page: number }) {
  const sp = new URLSearchParams();
  if (params.q.trim()) {
    sp.set("query", params.q.trim());
  }
  if (params.status) {
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

export function ReportReviewPageClient({
  reports,
  total,
  page,
  totalPages,
  currentQuery,
  currentStatus,
}: ReportReviewPageClientProps) {
  const router = useRouter();
  const toast = useToast();

  const [queryDraft, setQueryDraft] = React.useState(currentQuery ?? "");
  const [statusFilter, setStatusFilter] = React.useState(currentStatus);

  React.useEffect(() => {
    setQueryDraft(currentQuery ?? "");
    setStatusFilter(currentStatus);
  }, [currentQuery, currentStatus]);

  const [detailOpen, setDetailOpen] = React.useState(false);
  const [detailLoading, setDetailLoading] = React.useState(false);
  const [detail, setDetail] = React.useState<ReportDetail | null>(null);
  const [rejectReason, setRejectReason] = React.useState("");
  const [actionLoading, setActionLoading] = React.useState(false);

  function goToPage(nextPage: number) {
    router.push(
      `/report-review${toQueryString({
        q: queryDraft,
        status: statusFilter,
        page: nextPage,
      })}`,
    );
  }

  function submitSearch(e: React.FormEvent) {
    e.preventDefault();
    goToPage(1);
  }

  function onStatusChange(value: "submitted" | "published" | "rejected") {
    setStatusFilter(value);
    router.push(`/report-review${toQueryString({ q: queryDraft, status: value, page: 1 })}`);
  }

  async function openDetail(reportId: string) {
    setDetailOpen(true);
    setDetailLoading(true);
    setRejectReason("");

    const result = await getReviewReportDetailAction(reportId);
    setDetailLoading(false);

    if (!result.ok) {
      toast.error(result.error, { title: "Error" });
      setDetailOpen(false);
      return;
    }

    setDetail(result.data);
  }

  async function handleDownload(filePath: string) {
    if (!detail) {
      return;
    }

    const result = await getReportDownloadUrlAction({
      report_id: detail.id,
      file_path: filePath,
    });

    if (!result.ok) {
      toast.error(result.error, { title: "Error" });
      return;
    }

    window.open(result.data, "_blank", "noopener,noreferrer");
  }

  async function runAction(action: "approve" | "reject" | "reopen") {
    if (!detail) {
      return;
    }

    setActionLoading(true);

    const payload =
      action === "reject"
        ? { action, report_id: detail.id, reason: rejectReason }
        : { action, report_id: detail.id };

    const result = await executeReviewAction(payload);
    setActionLoading(false);

    if (!result.ok) {
      toast.error(result.error, { title: "Error" });
      return;
    }

    setDetail(result.data);
    if (action === "reject") {
      setRejectReason("");
    }

    toast.success("Action completed.", { title: "Success" });
    router.refresh();
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-white/10 bg-zinc-900/60 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
          <div>
            <div className="text-xl font-semibold text-zinc-50">Report Review</div>
            <div className="text-xs text-zinc-400">Total {total}</div>
          </div>
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
                value={statusFilter}
                onChange={(event) =>
                  onStatusChange(event.target.value as "submitted" | "published" | "rejected")
                }
                options={FILTER_OPTIONS}
              />
            </div>
            <Button type="submit">Search</Button>
          </form>
        </div>

        <Table>
          <THead>
            <TR>
              <TH>Title</TH>
              <TH>Status</TH>
              <TH>Owner</TH>
              <TH>Updated</TH>
              <TH className="text-right">Action</TH>
            </TR>
          </THead>
          <tbody>
            {reports.length === 0 ? (
              <TR>
                <TD colSpan={5} className="py-10 text-center text-zinc-400">
                  No reports found.
                </TD>
              </TR>
            ) : (
              reports.map((report) => (
                <TR key={report.id}>
                  <TD className="font-medium text-zinc-100">{report.title}</TD>
                  <TD>
                    <Badge tone={statusTone(report.status)}>{report.status}</Badge>
                  </TD>
                  <TD className="text-zinc-300">{`${report.owner_user_id.slice(0, 8)}...`}</TD>
                  <TD className="text-zinc-400">{formatDateTime(report.updated_at)}</TD>
                  <TD>
                    <div className="flex justify-end">
                      <ActionButton onClick={() => openDetail(report.id)}>Review</ActionButton>
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
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        title="Review Report"
        className="max-w-3xl"
        footer={
          <>
            <Button variant="ghost" type="button" onClick={() => setDetailOpen(false)}>
              Close
            </Button>
            {detail?.status === "submitted" ? (
              <>
                <Button
                  type="button"
                  variant="danger"
                  onClick={() => runAction("reject")}
                  isLoading={actionLoading}
                >
                  Reject
                </Button>
                <Button type="button" onClick={() => runAction("approve")} isLoading={actionLoading}>
                  Approve
                </Button>
              </>
            ) : null}
            {detail?.status === "rejected" ? (
              <Button type="button" onClick={() => runAction("reopen")} isLoading={actionLoading}>
                Reopen to Draft
              </Button>
            ) : null}
          </>
        }
      >
        {detailLoading ? (
          <div className="py-8 text-center text-zinc-400">Loading detail...</div>
        ) : detail ? (
          <div className="space-y-4">
            <div className="rounded-[12px] border border-white/10 bg-zinc-900/70 p-4">
              <div className="grid grid-cols-1 gap-2 text-sm md:grid-cols-2">
                <div>
                  <span className="text-zinc-500">Title:</span>{" "}
                  <span className="text-zinc-100">{detail.title}</span>
                </div>
                <div>
                  <span className="text-zinc-500">Type:</span>{" "}
                  <span className="text-zinc-100">{detail.report_type}</span>
                </div>
                <div>
                  <span className="text-zinc-500">Status:</span>{" "}
                  <Badge tone={statusTone(detail.status)}>{detail.status}</Badge>
                </div>
                <div>
                  <span className="text-zinc-500">Version:</span>{" "}
                  <span className="text-zinc-100">v{detail.current_version_no}</span>
                </div>
              </div>
            </div>

            <div className="rounded-[12px] border border-white/10 bg-zinc-900/70 p-4">
              <div className="mb-2 text-sm font-medium text-zinc-200">Files</div>
              <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                <div className="rounded-[8px] border border-white/10 bg-zinc-800/40 p-3 text-sm text-zinc-300">
                  <div className="mb-1 text-xs text-zinc-500">Report</div>
                  {detail.latest_version?.word_file_path ? (
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => handleDownload(detail.latest_version!.word_file_path!)}
                    >
                      Download
                    </Button>
                  ) : (
                    <span className="text-zinc-500">No file</span>
                  )}
                </div>
                <div className="rounded-[8px] border border-white/10 bg-zinc-800/40 p-3 text-sm text-zinc-300">
                  <div className="mb-1 text-xs text-zinc-500">Model</div>
                  {detail.latest_version?.model_file_path ? (
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => handleDownload(detail.latest_version!.model_file_path!)}
                    >
                      Download
                    </Button>
                  ) : (
                    <span className="text-zinc-500">No file</span>
                  )}
                </div>
              </div>
            </div>

            {detail.status === "submitted" ? (
              <Input
                label="Reject Note"
                placeholder="Note is required when rejecting"
                value={rejectReason}
                onChange={(event) => setRejectReason(event.target.value)}
              />
            ) : null}

            <div className="space-y-2 rounded-[12px] border border-white/10 bg-zinc-900/70 p-4">
              <div className="text-sm font-medium text-zinc-200">Report Status History</div>
              {detail.status_logs.length === 0 ? (
                <p className="text-sm text-zinc-500">No history.</p>
              ) : (
                detail.status_logs.map((item) => (
                  <div
                    key={item.id}
                    className="rounded-[8px] border border-white/10 bg-zinc-800/40 p-3 text-sm"
                  >
                    <div className="text-zinc-100">
                      {item.from_status} -&gt; {item.to_status} <Badge tone="zinc">v{item.version_no}</Badge>
                    </div>
                    <div className="mt-1 text-xs text-zinc-500">{formatDateTime(item.action_at)}</div>
                    {item.reason ? (
                      <div className="mt-1 text-xs text-amber-300">Note: {item.reason}</div>
                    ) : null}
                  </div>
                ))
              )}
            </div>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
