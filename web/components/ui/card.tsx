import * as React from "react";

import { cn } from "@/lib/cn";

export type CardProps = React.HTMLAttributes<HTMLDivElement>;

export function Card({ className, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-[12px] border border-white/10 bg-zinc-900 p-6",
        "transition-all duration-200 hover:-translate-y-[2px] hover:border-white/20 hover:shadow-[0_4px_12px_rgba(0,0,0,0.3)]",
        className,
      )}
      {...props}
    />
  );
}

