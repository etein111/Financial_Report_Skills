import { unstable_noStore as noStore } from "next/cache";

import { listUsers } from "../repo/users-admin-repo";
import { UsersPageClient } from "./users-page-client";

export async function UsersPage({
  searchParams,
}: {
  searchParams?: Record<string, string | string[] | undefined>;
}) {
  noStore();

  const rawQ = searchParams?.q;
  const q = typeof rawQ === "string" ? rawQ : Array.isArray(rawQ) ? rawQ[0] : "";

  const rawPage = searchParams?.page;
  const pageStr =
    typeof rawPage === "string"
      ? rawPage
      : Array.isArray(rawPage)
        ? rawPage[0]
        : "";
  const page = Math.max(1, Number.parseInt(pageStr || "1", 10) || 1);

  const data = await listUsers({ page, query: q || null });

  return (
    <UsersPageClient
      items={data.items}
      total={data.total}
      page={data.page}
      totalPages={data.totalPages}
      query={q}
    />
  );
}

