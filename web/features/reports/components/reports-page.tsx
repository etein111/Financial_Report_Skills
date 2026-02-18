import * as React from "react";

import type { ReportStatus } from "@/domain/schemas/report";
import { listAllActiveAnalysts } from "@/features/analyst-info/repo/analysts-repo";

import { listReportsAction } from "../actions";
import { ReportsPageClient } from "./reports-page-client";

export interface ReportsPageProps {
  searchParams: Promise<{
    page?: string;
    query?: string;
    status?: string;
  }>;
  userRole: "admin" | "sa" | "analyst";
  currentUserId: string;
}

const VALID_STATUSES = new Set<ReportStatus>([
  "draft",
  "submitted",
  "published",
  "rejected",
]);

export async function ReportsPage({
  searchParams,
  userRole,
  currentUserId,
}: ReportsPageProps) {
  const params = await searchParams;
  const page = Math.max(1, Number(params.page ?? 1) || 1);
  const query = params.query?.trim() || null;
  const rawStatus = params.status?.trim() || "";
  const status: ReportStatus | null =
    rawStatus && rawStatus !== "all" && VALID_STATUSES.has(rawStatus as ReportStatus)
      ? (rawStatus as ReportStatus)
      : null;

  const [listResult, analystsResult] = await Promise.all([
    listReportsAction({ page, query, status }),
    listAllActiveAnalysts(),
  ]);

  if (!listResult.ok) {
    return (
      <div className="flex items-center justify-center p-8">
        <p className="text-zinc-400">Failed to load reports: {listResult.error}</p>
      </div>
    );
  }

  const analysts = analystsResult.ok ? analystsResult.data : [];

  return (
    <ReportsPageClient
      reports={listResult.data.items}
      total={listResult.data.total}
      page={listResult.data.page}
      totalPages={listResult.data.totalPages}
      currentQuery={query}
      currentStatus={listResult.data.applied_status}
      userRole={userRole}
      currentUserId={currentUserId}
      analysts={analysts}
    />
  );
}
