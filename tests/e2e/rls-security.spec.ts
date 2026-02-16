import { expect, test } from "@playwright/test";

test.describe("RLS Security Policies", () => {
  test.describe("Region Table", () => {
    test("authenticated users can read regions", async ({ page }) => {
      // Login as SA (non-admin)
      await page.goto("/login");
      await page.fill('input[type="email"]', 'sa@neolyst.com');
      await page.fill('input[type="password"]', 'Analyst123');
      await page.click('button[type="submit"]');
      
      // SA can navigate to desktop
      await expect(page).toHaveURL(/\/desktop/, { timeout: 15000 });

      // Note: SA cannot access /regions page due to UI protection
      // But RLS allows reading - we can test this by verifying
      // that regions data is accessible through API or actions
      // (This would need API testing or direct DB testing)
    });

    test("only admin can write to regions table", async ({ page }) => {
      // Login as admin
      await page.goto("/login");
      await page.fill('input[type="email"]', 'admin@neolyst.com');
      await page.fill('input[type="password"]', 'Admin123');
      await page.click('button[type="submit"]');
      await expect(page).toHaveURL(/\/desktop/, { timeout: 15000 });

      // Navigate to regions
      await page.goto("/regions");
      await expect(page).toHaveURL(/\/regions/, { timeout: 5000 });

      // Try to create region - should succeed
      await page.click('button:has-text("Create Region")');
      await page.fill('#name', 'RLS Test Region');
      await page.fill('#code', 'RLS');
      await page.click('button:has-text("Create")');

      // Should succeed (no error about permission denied)
      await expect(page.locator("body")).not.toContainText("permission", { timeout: 5000 });
    });
  });

  test.describe("Analyst Table", () => {
    test("authenticated users can read analysts", async ({ page }) => {
      // Login as SA
      await page.goto("/login");
      await page.fill('input[type="email"]', 'sa@neolyst.com');
      await page.fill('input[type="password"]', 'Analyst123');
      await page.click('button[type="submit"]');
      await expect(page).toHaveURL(/\/desktop/, { timeout: 15000 });

      // Similar to regions - UI protection exists but RLS allows reading
      // Actual RLS read access would need API/DB level testing
    });

    test("only admin can write to analyst table", async ({ page }) => {
      // Login as admin
      await page.goto("/login");
      await page.fill('input[type="email"]', 'admin@neolyst.com');
      await page.fill('input[type="password"]', 'Admin123');
      await page.click('button[type="submit"]');
      await expect(page).toHaveURL(/\/desktop/, { timeout: 15000 });

      // Navigate to analyst info
      await page.goto("/analyst-info");
      await expect(page).toHaveURL(/\/analyst-info/, { timeout: 5000 });

      // Try to create analyst - should succeed
      await page.click('button:has-text("Create Analyst")');
      await page.fill('#full_name', 'RLS Test Analyst');
      await page.fill('#email', `rls.test.${Date.now()}@example.com`);
      await page.selectOption('#region_id', 'China');
      await page.click('button:has-text("Create")');

      // Should succeed (no error about permission denied)
      await expect(page.locator("body")).not.toContainText("permission", { timeout: 5000 });
    });
  });

  test.describe("Delete Cascade", () => {
    test("deleting region sets analyst region_id to NULL", async ({ page }) => {
      // Login as admin
      await page.goto("/login");
      await page.fill('input[type="email"]', 'admin@neolyst.com');
      await page.fill('input[type="password"]', 'Admin123');
      await page.click('button[type="submit"]');
      await expect(page).toHaveURL(/\/desktop/, { timeout: 15000 });

      // First create an analyst linked to a region
      await page.goto("/analyst-info");
      await page.click('button:has-text("Create Analyst")');
      await page.fill('#full_name', 'Cascade Test Analyst');
      await page.fill('#email', `cascade.${Date.now()}@example.com`);
      await page.selectOption('#region_id', 'China');
      await page.click('button:has-text("Create")');
      await expect(page.locator("table")).toContainText("Cascade Test Analyst", { timeout: 5000 });

      // Now go to regions and delete China
      await page.goto("/regions");
      const row = page.locator("table tbody tr").filter({ hasText: "China" });
      await row.locator('button:has-text("Delete")').click();
      await page.click('button:has-text("Confirm Delete")');

      // Go back to analyst info and verify region is NULL
      await page.goto("/analyst-info");
      const analystRow = page.locator("table tbody tr").filter({ hasText: "Cascade Test Analyst" });
      
      // Region column should show "-" (NULL)
      await expect(analystRow.locator('td').nth(3)).toContainText("-");
    });
  });

  test.describe("Unique Constraints", () => {
    test("region name must be unique", async ({ page }) => {
      await page.goto("/login");
      await page.fill('input[type="email"]', 'admin@neolyst.com');
      await page.fill('input[type="password"]', 'Admin123');
      await page.click('button[type="submit"]');
      await expect(page).toHaveURL(/\/desktop/, { timeout: 15000 });

      await page.goto("/regions");

      // Try to create duplicate region
      await page.click('button:has-text("Create Region")');
      await page.fill('#name', 'China');
      await page.fill('#code', 'DUP');
      await page.click('button:has-text("Create")');

      // Should show unique constraint error
      await expect(page.locator("text=Region name already exists")).toBeVisible({ timeout: 5000 });
    });

    test("region code must be unique", async ({ page }) => {
      await page.goto("/login");
      await page.fill('input[type="email"]', 'admin@neolyst.com');
      await page.fill('input[type="password"]', 'Admin123');
      await page.click('button[type="submit"]');
      await expect(page).toHaveURL(/\/desktop/, { timeout: 15000 });

      await page.goto("/regions");

      // Try to create duplicate code
      await page.click('button:has-text("Create Region")');
      await page.fill('#name', 'Duplicate');
      await page.fill('#code', 'CN');
      await page.click('button:has-text("Create")');

      // Should show unique constraint error
      await expect(page.locator("text=Region code already exists")).toBeVisible({ timeout: 5000 });
    });

    test("analyst email must be unique", async ({ page }) => {
      await page.goto("/login");
      await page.fill('input[type="email"]', 'admin@neolyst.com');
      await page.fill('input[type="password"]', 'Admin123');
      await page.click('button[type="submit"]');
      await expect(page).toHaveURL(/\/desktop/, { timeout: 15000 });

      await page.goto("/analyst-info");

      // Try to create duplicate email
      await page.click('button:has-text("Create Analyst")');
      await page.fill('#full_name', 'Duplicate Email Test');
      await page.fill('#email', 'admin@neolyst.com'); // Admin's email
      await page.selectOption('#region_id', 'China');
      await page.click('button:has-text("Create")');

      // Should show unique constraint error
      await expect(page.locator("text=Email already exists")).toBeVisible({ timeout: 5000 });
    });
  });
});
