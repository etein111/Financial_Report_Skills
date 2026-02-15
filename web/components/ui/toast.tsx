"use client";

import * as React from "react";

import { cn } from "@/lib/cn";

type ToastType = "success" | "error";

type ToastItem = {
  id: string;
  type: ToastType;
  title?: string;
  message: string;
  durationMs: number;
};

type ToastContextValue = {
  success: (message: string, opts?: { title?: string; durationMs?: number }) => void;
  error: (message: string, opts?: { title?: string; durationMs?: number }) => void;
};

const ToastContext = React.createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<ToastItem[]>([]);

  const push = React.useCallback(
    (type: ToastType, message: string, opts?: { title?: string; durationMs?: number }) => {
      const id = crypto.randomUUID();
      const durationMs = opts?.durationMs ?? (type === "success" ? 3000 : 5000);
      const toast: ToastItem = { id, type, title: opts?.title, message, durationMs };
      setToasts((prev) => [toast, ...prev]);
      window.setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, durationMs);
    },
    [],
  );

  const value: ToastContextValue = React.useMemo(
    () => ({
      success: (message, opts) => push("success", message, opts),
      error: (message, opts) => push("error", message, opts),
    }),
    [push],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastViewport toasts={toasts} />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = React.useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

function ToastViewport({ toasts }: { toasts: ToastItem[] }) {
  return (
    <div
      className="fixed left-1/2 top-6 z-[60] flex w-full max-w-sm -translate-x-1/2 flex-col gap-3"
      aria-live="polite"
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          className={cn(
            "rounded-[12px] border px-4 py-3 text-sm shadow-[0_10px_40px_-3px_rgba(0,0,0,0.5)]",
            "backdrop-blur-md",
            "animate-[toast-in_200ms_ease-out]",
            t.type === "success"
              ? "border-emerald-500/30 bg-zinc-900/80 text-zinc-100"
              : "border-red-500/30 bg-zinc-900/80 text-zinc-100",
          )}
        >
          <div className="flex items-start gap-3">
            <div className={cn(
              "flex h-5 w-5 shrink-0 items-center justify-center rounded-full",
              t.type === "success" ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"
            )}>
              {t.type === "success" ? (
                <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              )}
            </div>
            <div className="min-w-0 flex-1">
              {t.title ? <div className="font-medium text-zinc-50">{t.title}</div> : null}
              <div className="break-words text-zinc-300">{t.message}</div>
            </div>
          </div>
        </div>
      ))}
      <style jsx global>{`
        @keyframes toast-in {
          from {
            transform: translateY(-8px);
            opacity: 0;
          }
          to {
            transform: translateY(0);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
}

