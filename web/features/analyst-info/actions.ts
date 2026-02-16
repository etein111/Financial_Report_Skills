"use server";

import { revalidatePath } from "next/navigation";

import {
  analystCreateSchema,
  analystUpdateSchema,
} from "@/domain/schemas/analyst";
import { err, ok, type Result } from "@/lib/result";
import { requireAdmin } from "@/lib/supabase/server";

import {
  createAnalyst as createAnalystRepo,
  deleteAnalyst as deleteAnalystRepo,
  getRegionsForSelect as getRegionsForSelectRepo,
  listAnalysts as listAnalystsRepo,
  type Analyst,
  type PaginatedList,
  updateAnalyst as updateAnalystRepo,
} from "./repo/analysts-repo";

async function requireAdminOrThrow() {
  await requireAdmin();
}

/**
 * List analysts with pagination and search
 */
export async function listAnalystsAction(input: {
  page?: number;
  query?: string | null;
}): Promise<Result<PaginatedList<Analyst>>> {
  await requireAdminOrThrow();

  const page = Math.max(1, input.page ?? 1);
  const query = input.query ?? null;

  try {
    const data = await listAnalystsRepo({ page, query });
    return ok(data);
  } catch {
    return err("Failed to list analysts.");
  }
}

/**
 * Create a new analyst
 */
export async function createAnalystAction(input: unknown): Promise<Result<Analyst>> {
  await requireAdminOrThrow();

  const parsed = analystCreateSchema.safeParse(input);
  if (!parsed.success) {
    return err(parsed.error.issues[0]?.message ?? "Invalid input.");
  }

  try {
    const data = await createAnalystRepo(parsed.data);
    revalidatePath("/analyst-info");
    return ok(data);
  } catch {
    return err("Failed to create analyst.");
  }
}

/**
 * Update an existing analyst
 */
export async function updateAnalystAction(
  id: string,
  input: unknown
): Promise<Result<Analyst>> {
  await requireAdminOrThrow();

  const parsed = analystUpdateSchema.safeParse(input);
  if (!parsed.success) {
    return err(parsed.error.issues[0]?.message ?? "Invalid input.");
  }

  try {
    const data = await updateAnalystRepo(id, parsed.data);
    revalidatePath("/analyst-info");
    return ok(data);
  } catch {
    return err("Failed to update analyst.");
  }
}

/**
 * Delete an analyst
 */
export async function deleteAnalystAction(id: string): Promise<Result<null>> {
  await requireAdminOrThrow();

  try {
    await deleteAnalystRepo(id);
    revalidatePath("/analyst-info");
    return ok(null);
  } catch {
    return err("Failed to delete analyst.");
  }
}

/**
 * Get all regions for form dropdown
 */
export async function getRegionsForSelectAction(): Promise<
  Result<{ id: string; name: string; code: string }[]>
> {
  await requireAdminOrThrow();

  try {
    const data = await getRegionsForSelectRepo();
    return ok(data);
  } catch {
    return err("Failed to fetch regions.");
  }
}
