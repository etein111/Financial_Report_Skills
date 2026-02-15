#!/usr/bin/env node
/**
 * Initialize default admin user using Supabase Admin API.
 *
 * Usage:
 *   node web/scripts/init-default-admin.mjs
 *
 * Environment variables (from web/.env):
 *   - NEXT_PUBLIC_SUPABASE_URL
 *   - SUPABASE_SERVICE_ROLE_KEY
 *
 * This script uses the Admin API instead of direct SQL INSERT,
 * which ensures all required fields are properly set by gotrue.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { createClient } from "@supabase/supabase-js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Load .env
function loadDotenv(filePath) {
  if (!fs.existsSync(filePath)) return;
  const raw = fs.readFileSync(filePath, "utf8");
  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq < 0) continue;
    const key = trimmed.slice(0, eq).trim();
    const value = trimmed.slice(eq + 1).trim();
    if (!key) continue;
    if (!(key in process.env)) process.env[key] = value;
  }
}

loadDotenv(path.join(__dirname, "..", ".env"));

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL;
const SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!SUPABASE_URL || !SERVICE_ROLE_KEY) {
  console.error("Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY");
  process.exit(1);
}

// Default admin config
const DEFAULT_ADMIN = {
  email: "admin@example.com",
  password: "ChangeMe123!",
  full_name: "System Administrator",
  role: "admin",
};

async function main() {
  const supabase = createClient(SUPABASE_URL, SERVICE_ROLE_KEY, {
    auth: { autoRefreshToken: false, persistSession: false },
  });

  // Check if user already exists
  const { data: existingUsers, error: listError } = await supabase.auth.admin.listUsers();
  if (listError) {
    console.error("Failed to list users:", listError.message);
    process.exit(1);
  }

  const existing = existingUsers.users.find(
    (u) => u.email.toLowerCase() === DEFAULT_ADMIN.email.toLowerCase()
  );

  if (existing) {
    console.log(`User ${DEFAULT_ADMIN.email} already exists.`);
    console.log("  ID:", existing.id);
    console.log("  Role:", existing.app_metadata?.role || "none");

    // Ensure role is set
    if (existing.app_metadata?.role !== DEFAULT_ADMIN.role) {
      console.log("  Updating role to", DEFAULT_ADMIN.role);
      await supabase.auth.admin.updateUserById(existing.id, {
        app_metadata: { ...existing.app_metadata, role: DEFAULT_ADMIN.role },
      });
    }
    return;
  }

  // Create new admin user
  console.log(`Creating admin user: ${DEFAULT_ADMIN.email}`);

  const { data, error } = await supabase.auth.admin.createUser({
    email: DEFAULT_ADMIN.email,
    password: DEFAULT_ADMIN.password,
    email_confirm: true,
    user_metadata: {
      full_name: DEFAULT_ADMIN.full_name,
    },
    app_metadata: {
      role: DEFAULT_ADMIN.role,
    },
  });

  if (error) {
    console.error("Failed to create user:", error.message);
    process.exit(1);
  }

  console.log("User created successfully!");
  console.log("  ID:", data.user.id);
  console.log("  Email:", data.user.email);
  console.log("  Role:", data.user.app_metadata?.role);
  console.log("\nPlease change the default password after first login.");
}

main().catch((e) => {
  console.error("Error:", e.message);
  process.exit(1);
});
