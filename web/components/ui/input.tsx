import * as React from "react";

import { cn } from "@/lib/cn";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  error?: string;
};

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, id, ...props }, ref) => {
    const generatedId = React.useId();
    const inputId = id ?? generatedId;

    return (
      <div className="space-y-1">
        {label ? (
          <label
            className="text-sm font-medium text-zinc-300"
            htmlFor={inputId}
          >
            {label}
          </label>
        ) : null}
        <input
          ref={ref}
          id={inputId}
          className={cn(
            "w-full rounded-[8px] border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-100",
            "placeholder:text-zinc-500",
            "outline-none ring-offset-0",
            "focus-visible:ring-2 focus-visible:ring-blue-500/60",
            error && "border-red-500 focus-visible:ring-red-500/50",
            className,
          )}
          {...props}
        />
        {error ? <p className="text-xs text-red-500">{error}</p> : null}
      </div>
    );
  },
);

Input.displayName = "Input";
