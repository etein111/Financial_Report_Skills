#!/usr/bin/env node
/**
 * Seed preset regions to cloud Supabase
 * Usage: node scripts/seed-regions.mjs
 */

import { createClient } from '@supabase/supabase-js';
// Use: node --env-file=.env scripts/seed-regions.mjs

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!supabaseUrl || !serviceRoleKey) {
  console.error('Error: NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set');
  process.exit(1);
}

const supabase = createClient(supabaseUrl, serviceRoleKey, {
  auth: {
    autoRefreshToken: false,
    persistSession: false
  }
});

const REGIONS = [
  { name: 'China', code: 'CN' },
  { name: 'Hong Kong', code: 'HK' },
  { name: 'Japan', code: 'JP' },
  { name: 'Taiwan', code: 'TW' },
  { name: 'Korea', code: 'KR' },
  { name: 'India', code: 'IN' },
  { name: 'Macau', code: 'MO' },
  { name: 'US', code: 'US' }
];

async function main() {
  console.log('Seeding regions to', supabaseUrl);

  // Check existing regions first
  const { data: existing, error: checkError } = await supabase
    .from('region')
    .select('name');

  if (checkError) {
    console.error('Error checking existing regions:', checkError.message);
    process.exit(1);
  }

  console.log(`Found ${existing.length} existing regions:`, existing.map(r => r.name).join(', '));

  // Insert new regions (upsert to handle conflicts)
  const { data, error } = await supabase
    .from('region')
    .upsert(REGIONS, { onConflict: 'name', ignoreDuplicates: true })
    .select();

  if (error) {
    console.error('Error seeding regions:', error.message);
    process.exit(1);
  }

  console.log(`Seeded ${data.length} regions:`, data.map(r => r.name).join(', '));

  // Verify final count
  const { data: final } = await supabase.from('region').select('name');
  console.log(`Total regions in database: ${final.length}`);
}

main();
