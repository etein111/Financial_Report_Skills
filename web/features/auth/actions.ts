"use server";

import { redirect } from "next/navigation";

import { err, ok, type Result } from "@/lib/result";
import { requestPasswordReset, signInWithPassword, signOut } from "./repo/auth-repo";

function isValidEmail(email: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

type AuthActionState = Result<null> | null;

export async function signInWithPasswordAction(
  _prev: AuthActionState,
  formData: FormData,
): Promise<AuthActionState> {
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");

  if (!email) return err("Email is required");
  if (!isValidEmail(email)) return err("Invalid email format");
  if (!password) return err("Password is required");

  const res = await signInWithPassword({ email, password });
  if (!res.ok) {
    // Don't leak backend details.
    return err("Invalid email or password.");
  }

  redirect("/desktop");
}

export async function requestPasswordResetAction(
  _prev: AuthActionState,
  formData: FormData,
): Promise<AuthActionState> {
  const email = String(formData.get("email") ?? "").trim();
  if (!email) return err("Email is required");
  if (!isValidEmail(email)) return err("Invalid email format");

  // Avoid email enumeration: always show success for valid email format.
  await requestPasswordReset({ email });

  return ok(null);
}

export async function signOutAction(): Promise<void> {
  await signOut();
  redirect("/login");
}
