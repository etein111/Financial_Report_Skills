"use server";

import { redirect } from "next/navigation";

import type { UserRole } from "@/domain/user";
import { err, ok, type Result } from "@/lib/result";
import { requireAdmin } from "@/lib/supabase/server";

import {
  banUser,
  deleteUser,
  inviteUser,
  resetUserPassword,
  setUserRole,
  unbanUser,
  updateUser,
} from "./repo/users-admin-repo";

function isValidEmail(email: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function parseRole(raw: unknown): UserRole | null {
  return raw === "admin" || raw === "sa" || raw === "analyst" ? raw : null;
}

async function requireAdminOrRedirect403() {
  try {
    await requireAdmin();
  } catch {
    redirect("/403");
  }
}

export async function inviteUserAction(input: {
  email: string;
  fullName: string;
  role: UserRole;
}): Promise<Result<{ id: string }>> {
  await requireAdminOrRedirect403();

  const email = input.email.trim();
  const fullName = input.fullName.trim();

  if (!email) return err("Email is required.");
  if (!isValidEmail(email)) return err("Invalid email address.");
  if (!fullName) return err("Name is required.");
  if (!parseRole(input.role)) return err("Invalid role.");

  try {
    const data = await inviteUser({ email, fullName, role: input.role });
    return ok(data);
  } catch {
    return err("Failed to invite user.");
  }
}

export async function updateUserAction(input: {
  id: string;
  email: string;
  fullName: string;
}): Promise<Result<null>> {
  await requireAdminOrRedirect403();

  const id = input.id.trim();
  const email = input.email.trim();
  const fullName = input.fullName.trim();

  if (!id) return err("Invalid user.");
  if (!fullName) return err("Name is required.");
  if (!email) return err("Email is required.");
  if (!isValidEmail(email)) return err("Invalid email address.");

  try {
    await updateUser({ id, email, fullName });
    return ok(null);
  } catch {
    return err("Failed to update user.");
  }
}

export async function setUserRoleAction(input: {
  id: string;
  role: UserRole;
}): Promise<Result<null>> {
  await requireAdminOrRedirect403();

  const id = input.id.trim();
  const role = parseRole(input.role);
  if (!id) return err("Invalid user.");
  if (!role) return err("Invalid role.");

  try {
    await setUserRole({ id, role });
    return ok(null);
  } catch {
    return err("Failed to update role.");
  }
}

export async function setUserBannedAction(input: {
  id: string;
  banned: boolean;
}): Promise<Result<null>> {
  await requireAdminOrRedirect403();

  const id = input.id.trim();
  if (!id) return err("Invalid user.");

  try {
    if (input.banned) await banUser({ id });
    else await unbanUser({ id });
    return ok(null);
  } catch {
    return err("Failed to update user status.");
  }
}

export async function resetUserPasswordAction(input: {
  id: string;
  newPassword: string;
}): Promise<Result<null>> {
  await requireAdminOrRedirect403();

  const id = input.id.trim();
  const newPassword = input.newPassword.trim();
  if (!id) return err("Invalid user.");
  if (!newPassword) return err("Password is required.");

  try {
    await resetUserPassword({ id, newPassword });
    return ok(null);
  } catch {
    return err("Failed to reset password.");
  }
}

export async function deleteUserAction(input: { id: string }): Promise<Result<null>> {
  await requireAdminOrRedirect403();

  const id = input.id.trim();
  if (!id) return err("Invalid user.");

  try {
    await deleteUser({ id });
    return ok(null);
  } catch {
    return err("Failed to delete user.");
  }
}

