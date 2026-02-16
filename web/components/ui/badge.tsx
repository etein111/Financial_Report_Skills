import * as React from "react";

import { cn } from "@/lib/cn";

export type BadgeTone =
  | "zinc"
  | "blue"
  | "amber"
  | "green"
  | "red"
  | "success"
  | "secondary";

export type BadgeProps = React.HTMLAttributes<HTMLSpanElement> & {
  tone?: BadgeTone;
  variant?: "success" | "secondary";
};

export function Badge({
  className,
  tone = "zinc",
  variant,
  ...props
}: BadgeProps) {
  // Support variant prop for backward compatibility
  const effectiveTone = variant || tone;

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        effectiveTone === "zinc" && "bg-white/10 text-zinc-200",
        effectiveTone === "blue" && "bg-blue-500/15 text-blue-200",
        effectiveTone === "amber" && "bg-amber-500/15 text-amber-200",
        effectiveTone === "green" && "bg-green-500/15 text-green-200",
        effectiveTone === "red" && "bg-red-500/15 text-red-200",
        effectiveTone === "success" && "bg-green-500/15 text-green-200",
        effectiveTone === "secondary" && "bg-white/10 text-zinc-400",
        className,
      )}
      {...props}
    />
  );
}

Badge.displayName = "Badge";
