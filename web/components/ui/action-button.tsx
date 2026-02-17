import { cn } from "@/lib/cn";

export type ActionButtonTone = "default" | "danger";

export type ActionButtonProps = {
  children: React.ReactNode;
  onClick: () => void;
  tone?: ActionButtonTone;
  disabled?: boolean;
};

export function ActionButton({
  children,
  onClick,
  tone = "default",
  disabled = false,
}: ActionButtonProps) {
  return (
    <button
      type="button"
      disabled={disabled}
      className={cn(
        "rounded-[6px] border border-white/10 px-3 py-1 text-xs font-medium",
        "transition-colors duration-200",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/60",
        "disabled:cursor-not-allowed disabled:opacity-50",
        tone === "danger"
          ? "bg-red-600/20 text-red-100 hover:bg-red-600/30"
          : "bg-zinc-800 text-zinc-100 hover:bg-zinc-700",
      )}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
