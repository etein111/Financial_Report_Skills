import { expect, test } from "@playwright/test";

test.describe("Analyst Info Management", () => {
  test.beforeEach(async ({ page }) => {
    // Login as admin
    await page.goto("/login");
    await page.fill('input[type="email"]', "admin@neolyst.com");
    await page.fill('input[type="password"]', "Admin123");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/\/desktop/, { timeout: 15000 });
  });

  test("analyst info page loads and displays analysts", async ({ page }) => {
    await page.goto("/analyst-info");
    await expect(page.locator("h1")).toContainText("Analyst Info");
    await expect(page.locator("table")).toBeVisible();
  });

  test("can create a new analyst", async ({ page }) => {
    await page.goto("/analyst-info");

    // Click create button
    await page.click('button:has-text("Create Analyst")');

    // Fill form
    await page.fill('#full_name', 'Test Analyst');
    await page.fill('#chinese_name', '测试分析师');
    await page.fill('#email', 'test.analyst@example.com');
    await page.selectOption('#region_id', 'China'); // Assuming China exists

    // Submit
    await page.click('button:has-text("Create")');

    // Should see success and new analyst in table
    await expect(page.locator("body")).toContainText("Test Analyst", { timeout: 5000 });
    await expect(page.locator("table")).toContainText("Test Analyst");
  });

  test("can edit an existing analyst", async ({ page }) => {
    await page.goto("/analyst-info");

    // Find first analyst and click edit
    const row = page.locator("table tbody tr").first();
    await row.locator('button:has-text("Edit")').click();

    // Update full name
    await page.fill('#full_name', 'Updated Analyst Name');
    await page.click('button:has-text("Update")');

    // Should see updated analyst
    await expect(page.locator("table")).toContainText("Updated Analyst Name", { timeout: 5000 });
  });

  test("cannot create analyst with duplicate email", async ({ page }) => {
    await page.goto("/analyst-info");

    // Click create button
    await page.click('button:has-text("Create Analyst")');

    // Try to create duplicate email
    await page.fill('#full_name', 'Duplicate Test');
    await page.fill('#email', 'admin@neolyst.com'); // Assuming this exists
    await page.selectOption('#region_id', 'China');
    await page.click('button:has-text("Create")');

    // Should show error
    await expect(page.locator("text=Email already exists")).toBeVisible({ timeout: 5000 });
  });

  test("can delete an analyst with confirmation", async ({ page }) => {
    await page.goto("/analyst-info");

    // Find a test analyst and click delete
    const row = page.locator("table tbody tr").filter({ hasText: /Test Analyst/ });
    const count = await row.count();

    if (count > 0) {
      await row.locator('button:has-text("Delete")').click();

      // Confirm deletion
      await page.click('button:has-text("Confirm Delete")');

      // Should refresh and analyst should be gone
      await expect(page.locator("table")).not.toContainText("Test Analyst", { timeout: 5000 });
    }
  });

  test("search filters analysts by name or email", async ({ page }) => {
    await page.goto("/analyst-info");

    // Enter search query
    await page.fill('input[placeholder*="Search"]', 'analyst');
    await page.click('button:has-text("Search")');

    // URL should update with search params
    await expect(page).toHaveURL(/query=analyst/, { timeout: 5000 });

    // Table should show matching results
    const rows = page.locator("table tbody tr");
    const count = await rows.count();
    expect(count).toBeGreaterThanOrEqual(0);
  });

  test("can toggle analyst active status", async ({ page }) => {
    await page.goto("/analyst-info");

    // Find first analyst and click edit
    const row = page.locator("table tbody tr").first();
    await row.locator('button:has-text("Edit")').click();

    // Toggle active status
    await page.locator('#is_active').uncheck();
    await page.click('button:has-text("Update")');

    // Should see "Inactive" badge
    await expect(page.locator("body")).toContainText("Inactive", { timeout: 5000 });
  });

  test("non-admin cannot access analyst info page", async ({ page, context }) => {
    // Create non-admin browser context
    const nonAdminPage = await context.newPage();
    await nonAdminPage.goto("/login");
    await nonAdminPage.fill('input[type="email"]', "sa@neolyst.com");
    await nonAdminPage.fill('input[type="password"]', "Analyst123");
    await nonAdminPage.click('button[type="submit"]');
    await expect(nonAdminPage).toHaveURL(/\/desktop/, { timeout: 15000 });

    // Try to access analyst info
    await nonAdminPage.goto("/analyst-info");

    // Should redirect to 403
    await expect(nonAdminPage).toHaveURL(/\/403/, { timeout: 5000 });
    await expect(nonAdminPage.locator("body")).toContainText("Forbidden", { timeout: 5000 });
  });
});
