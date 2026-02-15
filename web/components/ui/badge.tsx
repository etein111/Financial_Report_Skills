import * as React from "react";

import { cn } from "@/lib/cn";

export type BadgeTone = "zinc" | "blue" | "amber" | "green" | "red";

export type BadgeProps = React.HTMLAttributes<HTMLSpanElement> & {
  tone?: BadgeTone;
};

export function Badge({ className, tone = "zinc", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        tone === "zinc" && "bg-white/10 text-zinc-200",
        tone === "blue" && "bg-blue-500/15 text-blue-200",
        tone === "amber" && "bg-amber-500/15 text-amber-200",
        tone === "green" && "bg-green-500/15 text-green-200",
        tone === "red" && "bg-red-500/15 text-red-200",
        className,
      )}
      {...props}
    />
  );
}

Badge.displayName = "Badge";

