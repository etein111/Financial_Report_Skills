import { Card } from "@/components/ui/card";

export default function ForbiddenPage() {
  return (
    <div className="flex min-h-screen items-center justify-center px-6">
      <Card className="w-full max-w-md text-center">
        <h1 className="text-xl font-semibold text-zinc-100">403</h1>
        <p className="mt-2 text-sm text-zinc-400">No permission</p>
      </Card>
    </div>
  );
}

