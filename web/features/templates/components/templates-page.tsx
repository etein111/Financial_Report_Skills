import * as React from "react";

import { listTemplatesGroupedAction } from "../actions";
import { TemplatesPageClient } from "./templates-page-client";

export async function TemplatesPage() {
  const result = await listTemplatesGroupedAction();

  if (!result.ok) {
    return (
      <div className="flex items-center justify-center p-8">
        <p className="text-zinc-400">Failed to load templates: {result.error}</p>
      </div>
    );
  }

  const templateGroups = result.data;

  return <TemplatesPageClient templateGroups={templateGroups} />;
}
