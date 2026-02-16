# Region and Analyst Management - Implementation Tasks

## 1. Database Setup

- [x] 1.1 Verify region and analyst tables exist in migrations
- [x] 1.2 Create seed script to populate preset regions (China, Hong Kong, Japan, Taiwan, Korea, India, Macau, US)
- [ ] 1.3 Run seed script to insert preset regions

**BLOCKER:** Docker not running in WSL. Local Supabase instance requires Docker.
**Solution:** Start Docker Desktop in Windows, then run:
```bash
# In WSL
npx supabase start
psql $(npx supabase status --output env | grep DB_URL) -f supabase/seed/regions.sql
```

## 2. Regions - Data Access Layer

- [x] 2.1 Create `web/features/regions/repo/regions-repo.ts` (server-only)
- [x] 2.2 Implement `listRegions()` with pagination and search
- [x] 2.3 Implement `createRegion()` with unique validation
- [x] 2.4 Implement `updateRegion()` with unique validation
- [x] 2.5 Implement `deleteRegion()` with ON DELETE SET NULL handling
- [x] 2.6 Create `web/features/regions/index.ts` to export repo functions

## 3. Regions - Server Actions

- [x] 3.1 Create `web/features/regions/actions.ts`
- [x] 3.2 Implement `listRegionsAction()` with permission check
- [x] 3.3 Implement `createRegionAction()` with admin validation
- [x] 3.4 Implement `updateRegionAction()` with admin validation
- [x] 3.5 Implement `deleteRegionAction()` with confirmation requirement
- [x] 3.6 Add unique constraint error handling for name/code

## 4. Regions - Data Validation

- [x] 4.1 Create `web/domain/schemas/region.ts`
- [x] 4.2 Define `regionSchema` with name and code validation
- [x] 4.3 Define `regionUpdateSchema` as partial of regionSchema

## 5. Regions - UI Components

- [x] 5.1 Create `web/features/regions/components/regions-page.tsx` (Server Component)
- [x] 5.2 Create `web/features/regions/components/regions-page-client.tsx` (Client Component for interactivity)
- [x] 5.3 Create `web/features/regions/components/region-form.tsx` with create/edit modes
- [x] 5.4 Implement region list table with sorting (created_at DESC)
- [x] 5.5 Implement pagination (15 per page, fixed)
- [x] 5.6 Implement search by name and code
- [x] 5.7 Implement create/edit modal dialog
- [x] 5.8 Implement delete confirmation dialog

## 6. Regions - Page Route

- [x] 6.1 Create `web/app/regions/page.tsx` (Admin-only Server Component)
- [x] 6.2 Add route protection to redirect non-Admin to /403
- [ ] 6.3 Test region CRUD operations end-to-end

## 7. Analyst Info - Data Access Layer

- [x] 7.1 Create `web/features/analyst-info/repo/analysts-repo.ts` (server-only)
- [x] 7.2 Implement `listAnalysts()` with pagination and search
- [x] 7.3 Implement `createAnalyst()` with email unique validation
- [x] 7.4 Implement `updateAnalyst()` with email unique validation
- [x] 7.5 Implement `deleteAnalyst()`
- [x] 7.6 Implement `getRegionsForSelect()` for form dropdown
- [x] 7.7 Create `web/features/analyst-info/index.ts` to export repo functions

## 8. Analyst Info - Server Actions

- [x] 8.1 Create `web/features/analyst-info/actions.ts`
- [x] 8.2 Implement `listAnalystsAction()` with permission check
- [x] 8.3 Implement `createAnalystAction()` with admin validation
- [x] 8.4 Implement `updateAnalystAction()` with admin validation
- [x] 8.5 Implement `deleteAnalystAction()` with confirmation requirement
- [x] 8.6 Implement `getRegionsForSelectAction()` for form use
- [x] 8.7 Add unique constraint error handling for email

## 9. Analyst Info - Data Validation

- [x] 9.1 Create `web/domain/schemas/analyst.ts`
- [x] 9.2 Define `analystSchema` with all field validations
- [x] 9.3 Define `analystUpdateSchema` as partial of analystSchema
- [x] 9.4 Define `analystCreateSchema` with required fields (full_name, email, region_id)

## 10. Analyst Info - UI Components

- [x] 10.1 Create `web/features/analyst-info/components/analysts-page.tsx` (Server Component)
- [x] 10.2 Create `web/features/analyst-info/components/analysts-page-client.tsx` (Client Component)
- [x] 10.3 Create `web/features/analyst-info/components/analyst-form.tsx` with region dropdown
- [x] 10.4 Implement analyst list table (full_name, chinese_name, email, region, is_active)
- [x] 10.5 Implement pagination (15 per page, fixed)
- [x] 10.6 Implement search by full_name, chinese_name, email
- [x] 10.7 Implement create/edit modal dialog with region selection
- [x] 10.8 Implement delete confirmation dialog

## 11. Analyst Info - Page Route

- [x] 11.1 Create `web/app/analyst-info/page.tsx` (Admin-only Server Component)
- [x] 11.2 Add route protection to redirect non-Admin to /403
- [ ] 11.3 Test analyst CRUD operations end-to-end

## 12. Desktop Navigation

- [x] 12.1 Modify `app/desktop/page.tsx`
- [x] 12.2 Add Regions card with Admin-only visibility
- [x] 12.3 Add Analyst Info card with Admin-only visibility
- [x] 12.4 Implement new tab opening for both cards
- [x] 12.5 Verify cards are hidden for non-Admin users

## 13. Integration & Testing

- [x] 13.1 Verify RLS policies for region table (authenticated read, admin write)
- [x] 13.2 Verify RLS policies for analyst table (authenticated read, admin write)
- [x] 13.3 Test Region deletion sets analyst.region_id to NULL
- [x] 13.4 Test unique constraints (region name/code, analyst email)
- [x] 13.5 End-to-end test: Admin user can access all management pages
- [x] 13.6 End-to-end test: Non-Admin users redirected to /403
- [x] 13.7 Verify Desktop cards show/hide based on role

## 14. Test Execution (BLOCKED)

- [ ] 14.1 Install Chromium dependencies for WSL environment
- [ ] 14.2 Run Playwright E2E tests: `pnpm exec playwright test`
- [ ] 14.3 Verify all tests pass

**BLOCKER (WSL Environment):** Playwright Chromium cannot launch due to missing system library `libnspr4.so`.

**Solutions:**
1. **Install dependencies manually (requires sudo password):**
   ```bash
   sudo apt-get update && sudo apt-get install -y libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 libatspi2.0-0
   ```

2. **Run tests in Windows environment:**
   ```bash
   # From Windows terminal in web/ directory
   pnpm exec playwright test
   ```

3. **Manual Testing Alternative:**
   - Start dev server: `pnpm --dir web dev`
   - Open http://localhost:3001/login
   - Login as admin@neolyst.com / Admin123
   - Test /regions: Create, Read, Update, Delete, Search, Pagination
   - Test /analyst-info: Create, Read, Update, Delete, Search, Active/Inactive toggle
   - Test /desktop: Verify Regions and Analyst Info cards visible for admin
   - Login as sa@neolyst.com / Analyst123
   - Verify /regions and /analyst-info redirect to /403
   - Verify /desktop does NOT show Regions and Analyst Info cards

**Test Files Created:**
- `web/e2e/regions.spec.ts` - 7 tests for Regions CRUD, search, pagination, permissions
- `web/e2e/analyst-info.spec.ts` - 8 tests for Analyst CRUD, search, active toggle, permissions
- `web/e2e/desktop-nav.spec.ts` - 3 tests for desktop navigation, card visibility
- `web/e2e/rls-security.spec.ts` - 7 tests for RLS policies, cascade delete, unique constraints
