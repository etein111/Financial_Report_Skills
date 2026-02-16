import { expect, test } from "@playwright/test";

test.describe("Regions Management", () => {
  test.beforeEach(async ({ page }) => {
    // Login as admin
    await page.goto("/login");
    await page.fill('input[type="email"]', "admin@neolyst.com");
    await page.fill('input[type="password"]', "Admin123");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/\/desktop/, { timeout: 15000 });
  });

  test("regions page loads and displays regions", async ({ page }) => {
    await page.goto("/regions");
    await expect(page.locator("h1")).toContainText("Regions");
    await expect(page.locator("table")).toBeVisible();
  });

  test("can create a new region", async ({ page }) => {
    await page.goto("/regions");

    // Click create button
    await page.click('button:has-text("Create Region")');

    // Fill form
    await page.fill('#name', "Test Region");
    await page.fill('#code', "TR");

    // Submit
    await page.click('button:has-text("Create")');

    // Should see success and new region in table
    await expect(page.locator("body")).toContainText("Test Region", { timeout: 5000 });
    await expect(page.locator("table")).toContainText("Test Region");
  });

  test("can edit an existing region", async ({ page }) => {
    await page.goto("/regions");

    // Find China region and click edit
    const row = page.locator("table tbody tr").filter({ hasText: "China" });
    await row.locator('button:has-text("Edit")').click();

    // Update name
    await page.fill('#name', "China (Updated)");
    await page.click('button:has-text("Update")');

    // Should see updated region
    await expect(page.locator("table")).toContainText("China (Updated)", { timeout: 5000 });
  });

  test("cannot create region with duplicate name", async ({ page }) => {
    await page.goto("/regions");

    // Click create button
    await page.click('button:has-text("Create Region")');

    // Try to create duplicate
    await page.fill('#name', "China");
    await page.fill('#code', "CN2");
    await page.click('button:has-text("Create")');

    // Should show error
    await expect(page.locator("text=Region name already exists")).toBeVisible({ timeout: 5000 });
  });

  test("can delete a region with confirmation", async ({ page }) => {
    await page.goto("/regions");

    // Find a region and click delete
    const row = page.locator("table tbody tr").filter({ hasText: /China|Japan|Korea/ });
    await row.locator('button:has-text("Delete")').click();

    // Confirm deletion
    await page.click('button:has-text("Confirm Delete")');

    // Should refresh and region should be gone
    await expect(page.locator("table")).not.toContainText(/China|Japan|Korea/, { timeout: 5000 });
  });

  test("search filters regions by name", async ({ page }) => {
    await page.goto("/regions");

    // Enter search query
    await page.fill('input[placeholder*="Search"]', "China");
    await page.click('button:has-text("Search")');

    // URL should update with search params
    await expect(page).toHaveURL(/query=China/, { timeout: 5000 });

    // Table should only show matching regions
    const rows = page.locator("table tbody tr");
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);
  });

  test("non-admin cannot access regions page", async ({ page, context }) => {
    // Create non-admin browser context (login as SA)
    const nonAdminPage = await context.newPage();
    await nonAdminPage.goto("/login");
    await nonAdminPage.fill('input[type="email"]', "sa@neolyst.com");
    await nonAdminPage.fill('input[type="password"]', "Analyst123");
    await nonAdminPage.click('button[type="submit"]');
    await expect(nonAdminPage).toHaveURL(/\/desktop/, { timeout: 15000 });

    // Try to access regions
    await nonAdminPage.goto("/regions");

    // Should redirect to 403
    await expect(nonAdminPage).toHaveURL(/\/403/, { timeout: 5000 });
    await expect(nonAdminPage.locator("body")).toContainText("Forbidden", { timeout: 5000 });
  });
});
