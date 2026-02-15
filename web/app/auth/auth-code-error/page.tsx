import { Card } from "@/components/ui/card";

export default function AuthCodeErrorPage() {
  return (
    <div className="flex min-h-screen items-center justify-center px-6">
      <Card className="w-full max-w-md text-center">
        <h1 className="text-xl font-semibold text-zinc-100">
          Authentication Error
        </h1>
        <p className="mt-2 text-sm text-zinc-400">
          Something went wrong during authentication. Please try again.
        </p>
        <a
          href="/login"
          className="mt-6 inline-flex rounded-[6px] border border-white/10 bg-zinc-800 px-4 py-2 text-sm font-medium text-zinc-100 transition-colors duration-200 hover:bg-zinc-700"
        >
          Back to Login
        </a>
      </Card>
    </div>
  );
}

