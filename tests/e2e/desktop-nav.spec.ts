import { expect, test } from "@playwright/test";

test.describe("Desktop Navigation", () => {
  test.describe("Admin User", () => {
    test.beforeEach(async ({ page }) => {
      // Login as admin
      await page.goto("/login");
      await page.fill('input[type="email"]', "admin@neolyst.com");
      await page.fill('input[type="password"]', "Admin123");
      await page.click('button[type="submit"]');
      await expect(page).toHaveURL(/\/desktop/, { timeout: 15000 });
    });

    test("displays Regions and Analyst Info cards on desktop", async ({ page }) => {
      // Check Data Management section
      const dataSection = page.locator('section:has(h2:has-text("Data Management"))');

      // Should have Regions card
      await expect(dataSection.locator('a:has-text("Regions")')).toBeVisible();
      await expect(dataSection.locator('a:has-text("Regions")')).toHaveAttribute('href', '/regions');

      // Should have Analyst Info card
      await expect(dataSection.locator('a:has-text("Analyst Info")')).toBeVisible();
      await expect(dataSection.locator('a:has-text("Analyst Info")')).toHaveAttribute('href', '/analyst-info');

      // Should have User Management card
      await expect(dataSection.locator('a:has-text("User Management")')).toBeVisible();
    });

    test("cards open in new tab when clicked", async ({ page }) => {
      // Click Regions card
      const [regionsTab] = await Promise.all([
        page.waitForEvent('popup'),
        page.locator('a:has-text("Regions")').click(),
      ]);

      // Should open new tab
      await expect(regionsTab).toBeTruthy();

      // Close tab
      await regionsTab.close();
    });

    test("coming soon features are marked correctly", async ({ page }) => {
      // Check that some cards still show "Coming Soon"
      const badges = page.locator('section:has(h2:has-text("Reports")) .badge');

      const badgeTexts = await badges.allTextContents();
      expect(badgeTexts).toContain('Coming Soon');
    });
  });

  test.describe("Non-Admin User (SA/Analyst)", () => {
    test("does not display admin-only cards", async ({ page }) => {
      // Login as SA
      await page.goto("/login");
      await page.fill('input[type="email"]', "sa@neolyst.com");
      await page.fill('input[type="password"]', 'Analyst123');
      await page.click('button[type="submit"]');
      await expect(page).toHaveURL(/\/desktop/, { timeout: 15000 });

      // Data Management section should NOT have admin cards
      const dataSection = page.locator('section:has(h2:has-text("Data Management"))');

      // Should NOT see Regions card
      await expect(dataSection.locator('a:has-text("Regions")')).not.toBeVisible();

      // Should NOT see Analyst Info card
      await expect(dataSection.locator('a:has-text("Analyst Info")')).not.toBeVisible();

      // Should NOT see User Management card
      await expect(dataSection.locator('a:has-text("User Management")')).not.toBeVisible();
    });
  });

  test.describe("Unauthenticated User", () => {
    test("redirects to login when accessing desktop", async ({ page }) => {
      await page.goto("/desktop");

      // Should redirect to login
      await expect(page).toHaveURL(/\/login/, { timeout: 5000 });
    });
  });
});
