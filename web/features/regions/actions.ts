"use server";

import { revalidatePath } from "next/navigation";

import { regionSchema, regionUpdateSchema } from "@/domain/schemas/region";
import { err, ok, type Result } from "@/lib/result";
import { requireAdmin } from "@/lib/supabase/server";

import {
  createRegion as createRegionRepo,
  deleteRegion as deleteRegionRepo,
  listRegions as listRegionsRepo,
  type PaginatedList,
  type Region,
  updateRegion as updateRegionRepo,
} from "./repo/regions-repo";

async function requireAdminOrThrow() {
  await requireAdmin();
}

/**
 * List regions with pagination and search
 */
export async function listRegionsAction(input: {
  page?: number;
  query?: string | null;
}): Promise<Result<PaginatedList<Region>>> {
  await requireAdminOrThrow();

  const page = Math.max(1, input.page ?? 1);
  const query = input.query ?? null;

  try {
    const data = await listRegionsRepo({ page, query });
    return ok(data);
  catch {
    return err("Failed to list regions.");
  }
}

/**
 * Create a new region
 */
export async function createRegionAction(input: unknown): Promise<Result<Region>> {
  await requireAdminOrThrow();

  const parsed = regionSchema.safeParse(input);
  if (!parsed.success) {
    return err(parsed.error.issues[0]?.message ?? "Invalid input.");
  }

  try {
    const data = await createRegionRepo(parsed.data);
    revalidatePath("/regions");
    return ok(data);
  } catch {
    return err("Failed to create region.");
  }
}

/**
 * Update an existing region
 */
export async function updateRegionAction(
  id: string,
  input: unknown
): Promise<Result<Region>> {
  await requireAdminOrThrow();

  const parsed = regionUpdateSchema.safeParse(input);
  if (!parsed.success) {
    return err(parsed.error.issues[0]?.message ?? "Invalid input.");
  }

  try {
    const data = await updateRegionRepo(id, parsed.data);
    revalidatePath("/regions");
    return ok(data);
  } catch {
    return err("Failed to update region.");
  }
}

/**
 * Delete a region
 */
export async function deleteRegionAction(id: string): Promise<Result<null>> {
  await requireAdminOrThrow();

  try {
    await deleteRegionRepo(id);
    revalidatePath("/regions");
    return ok(null);
  } catch {
    return err("Failed to delete region.");
  }
}
