import * as React from "react";

import { listAllActiveAnalysts } from "@/features/analyst-info/repo/analysts-repo";
import { listAllRegions } from "@/features/regions/repo/regions-repo";
import { listAllActiveSectors } from "@/features/sectors/repo/sectors-repo";

import { listReportTypeOptionsAction } from "../actions";
import { NewReportPageClient } from "./new-report-page-client";

export interface NewReportPageProps {
  userRole: "admin" | "analyst";
}

export async function NewReportPage({ userRole }: NewReportPageProps) {
  const [typesResult, analystsResult, regionsResult, sectorsResult] =
    await Promise.all([
      listReportTypeOptionsAction(),
      listAllActiveAnalysts(),
      listAllRegions(),
      listAllActiveSectors(),
    ]);

  if (!typesResult.ok) {
    return (
      <div className="flex items-center justify-center p-8">
        <p className="text-zinc-400">
          Failed to load report type options: {typesResult.error}
        </p>
      </div>
    );
  }

  return (
    <NewReportPageClient
      userRole={userRole}
      reportTypes={typesResult.data}
      analysts={analystsResult.ok ? analystsResult.data : []}
      regions={regionsResult.ok ? regionsResult.data : []}
      sectors={sectorsResult.ok ? sectorsResult.data : []}
    />
  );
}
