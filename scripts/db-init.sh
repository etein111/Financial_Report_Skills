#!/usr/bin/env bash
#
# Database initialization script
# Runs migrations, SQL seed, and Auth user initialization
#
# Usage:
#   bash scripts/db-init.sh
#   # or
#   pnpm run db:init
#
# Prerequisites:
#   - Supabase CLI installed
#   - Project linked (supabase link --project-ref <ref>)
#   - Environment variables set (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
#

set -euo pipefail

echo "=== Database Initialization ==="
echo ""

echo "1. Pushing migrations..."
supabase db push --yes

echo ""
echo "2. Running SQL seed..."
supabase seed --local

echo ""
echo "3. Initializing Auth users..."
pnpm -s run seed:auth

echo ""
echo "=== Initialization Complete ==="
