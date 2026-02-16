# Region and Analyst Management - Implementation Tasks

## 1. Database Setup

- [ ] 1.1 Verify region and analyst tables exist in migrations
- [ ] 1.2 Create seed script to populate preset regions (China, Hong Kong, Japan, Taiwan, Korea, India, Macau, US)
- [ ] 1.3 Run seed script to insert preset regions

## 2. Regions - Data Access Layer

- [ ] 2.1 Create `web/features/regions/repo/regions-repo.ts` (server-only)
- [ ] 2.2 Implement `listRegions()` with pagination and search
- [ ] 2.3 Implement `createRegion()` with unique validation
- [ ] 2.4 Implement `updateRegion()` with unique validation
- [ ] 2.5 Implement `deleteRegion()` with ON DELETE SET NULL handling
- [ ] 2.6 Create `web/features/regions/index.ts` to export repo functions

## 3. Regions - Server Actions

- [ ] 3.1 Create `web/features/regions/actions.ts`
- [ ] 3.2 Implement `listRegionsAction()` with permission check
- [ ] 3.3 Implement `createRegionAction()` with admin validation
- [ ] 3.4 Implement `updateRegionAction()` with admin validation
- [ ] 3.5 Implement `deleteRegionAction()` with confirmation requirement
- [ ] 3.6 Add unique constraint error handling for name/code

## 4. Regions - Data Validation

- [ ] 4.1 Create `web/domain/schemas/region.ts`
- [ ] 4.2 Define `regionSchema` with name and code validation
- [ ] 4.3 Define `regionUpdateSchema` as partial of regionSchema

## 5. Regions - UI Components

- [ ] 5.1 Create `web/features/regions/components/regions-page.tsx` (Server Component)
- [ ] 5.2 Create `web/features/regions/components/regions-page-client.tsx` (Client Component for interactivity)
- [ ] 5.3 Create `web/features/regions/components/region-form.tsx` with create/edit modes
- [ ] 5.4 Implement region list table with sorting (created_at DESC)
- [ ] 5.5 Implement pagination (15 per page, fixed)
- [ ] 5.6 Implement search by name and code
- [ ] 5.7 Implement create/edit modal dialog
- [ ] 5.8 Implement delete confirmation dialog

## 6. Regions - Page Route

- [ ] 6.1 Create `web/app/regions/page.tsx` (Admin-only Server Component)
- [ ] 6.2 Add route protection to redirect non-Admin to /403
- [ ] 6.3 Test region CRUD operations end-to-end

## 7. Analyst Info - Data Access Layer

- [ ] 7.1 Create `web/features/analyst-info/repo/analysts-repo.ts` (server-only)
- [ ] 7.2 Implement `listAnalysts()` with pagination and search
- [ ] 7.3 Implement `createAnalyst()` with email unique validation
- [ ] 7.4 Implement `updateAnalyst()` with email unique validation
- [ ] 7.5 Implement `deleteAnalyst()`
- [ ] 7.6 Implement `getRegionsForSelect()` for form dropdown
- [ ] 7.7 Create `web/features/analyst-info/index.ts` to export repo functions

## 8. Analyst Info - Server Actions

- [ ] 8.1 Create `web/features/analyst-info/actions.ts`
- [ ] 8.2 Implement `listAnalystsAction()` with permission check
- [ ] 8.3 Implement `createAnalystAction()` with admin validation
- [ ] 8.4 Implement `updateAnalystAction()` with admin validation
- [ ] 8.5 Implement `deleteAnalystAction()` with confirmation requirement
- [ ] 8.6 Implement `getRegionsForSelectAction()` for form use
- [ ] 8.7 Add unique constraint error handling for email

## 9. Analyst Info - Data Validation

- [ ] 9.1 Create `web/domain/schemas/analyst.ts`
- [ ] 9.2 Define `analystSchema` with all field validations
- [ ] 9.3 Define `analystUpdateSchema` as partial of analystSchema
- [ ] 9.4 Define `analystCreateSchema` with required fields (full_name, email, region_id)

## 10. Analyst Info - UI Components

- [ ] 10.1 Create `web/features/analyst-info/components/analysts-page.tsx` (Server Component)
- [ ] 10.2 Create `web/features/analyst-info/components/analysts-page-client.tsx` (Client Component)
- [ ] 10.3 Create `web/features/analyst-info/components/analyst-form.tsx` with region dropdown
- [ ] 10.4 Implement analyst list table (full_name, chinese_name, email, region, is_active)
- [ ] 10.5 Implement pagination (15 per page, fixed)
- [ ] 10.6 Implement search by full_name, chinese_name, email
- [ ] 10.7 Implement create/edit modal dialog with region selection
- [ ] 10.8 Implement delete confirmation dialog

## 11. Analyst Info - Page Route

- [ ] 11.1 Create `web/app/analyst-info/page.tsx` (Admin-only Server Component)
- [ ] 11.2 Add route protection to redirect non-Admin to /403
- [ ] 11.3 Test analyst CRUD operations end-to-end

## 12. Desktop Navigation

- [ ] 12.1 Modify `features/desktop/components/desktop-page-client.tsx`
- [ ] 12.2 Add Regions card with Admin-only visibility
- [ ] 12.3 Add Analyst Info card with Admin-only visibility
- [ ] 12.4 Implement new tab opening for both cards
- [ ] 12.5 Verify cards are hidden for non-Admin users

## 13. Integration & Testing

- [ ] 13.1 Verify RLS policies for region table (authenticated read, admin write)
- [ ] 13.2 Verify RLS policies for analyst table (authenticated read, admin write)
- [ ] 13.3 Test Region deletion sets analyst.region_id to NULL
- [ ] 13.4 Test unique constraints (region name/code, analyst email)
- [ ] 13.5 End-to-end test: Admin user can access all management pages
- [ ] 13.6 End-to-end test: Non-Admin users redirected to /403
- [ ] 13.7 Verify Desktop cards show/hide based on role
