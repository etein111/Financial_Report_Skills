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
      className="fixed right-4 top-4 z-[60] flex w-full max-w-sm flex-col gap-2"
      aria-live="polite"
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          className={cn(
            "rounded-[8px] px-4 py-3 text-sm text-white shadow-[0_10px_15px_-3px_rgba(0,0,0,0.35)]",
            "animate-[toast-in_200ms_ease-out]",
            t.type === "success" ? "bg-green-500" : "bg-red-500",
          )}
        >
          <div className="flex items-start gap-2">
            <div className="pt-0.5">{t.type === "success" ? "✅" : "❌"}</div>
            <div className="min-w-0">
              {t.title ? <div className="font-semibold">{t.title}</div> : null}
              <div className="break-words">{t.message}</div>
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

