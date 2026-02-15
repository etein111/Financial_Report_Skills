import * as React from "react";

import { cn } from "@/lib/cn";

export type TableProps = React.TableHTMLAttributes<HTMLTableElement>;

export function Table({ className, ...props }: TableProps) {
  return (
    <div className="overflow-x-auto rounded-[12px] border border-white/10 bg-zinc-900">
      <table
        className={cn("min-w-full text-left text-sm", className)}
        {...props}
      />
    </div>
  );
}

Table.displayName = "Table";

export function THead({ className, ...props }: React.HTMLAttributes<HTMLElement>) {
  return (
    <thead
      className={cn("bg-zinc-800/50 text-zinc-400", className)}
      {...props}
    />
  );
}

THead.displayName = "THead";

export function TR({ className, ...props }: React.HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr
      className={cn("border-b border-white/10 hover:bg-zinc-800/30", className)}
      {...props}
    />
  );
}

TR.displayName = "TR";

export function TH({ className, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return <th className={cn("px-4 py-3 font-medium", className)} {...props} />;
}

TH.displayName = "TH";

export function TD({ className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={cn("px-4 py-3", className)} {...props} />;
}

TD.displayName = "TD";
