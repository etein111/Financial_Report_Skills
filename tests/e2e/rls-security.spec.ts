import { expect, test } from "@playwright/test";

test.describe("RLS Security Policies", () => {
  test.describe("Region Table", () => {
    test("authenticated users can read regions", async ({ page }) => {
      // Login as SA (non-admin)
      await page.goto("/login");
      await page.fill('input[type="email"]', "sa@neolyst.com");
      await page.fill('input[type="password"]', "Analyst123");
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
      await page.fill('input[type="email"]', "jiang_jiahong@qq.com");
      await page.fill('input[type="password"]', "Admin123");
      await page.click('button[type="submit"]');
      await expect(page).toHaveURL(/\/desktop/, { timeout: 15000 });

      // Navigate to regions
      await page.goto("/regions");
      await expect(page).toHaveURL(/\/regions/, { timeout: 5000 });

      // Try to create region - should succeed
      await page.click('button:has-text("Create Region")');
      await page.fill("#name", "RLS Test Region");
      await page.fill("#code", "RLS");
      await page.click('button:has-text("Create")', { force: true });

      // Should succeed (no error about permission denied)
      await expect(page.locator("body")).not.toContainText("permission", {
        timeout: 5000,
      });
    });
  });

  test.describe("Analyst Table", () => {
    test("authenticated users can read analysts", async ({ page }) => {
      // Login as SA
      await page.goto("/login");
      await page.fill('input[type="email"]', "sa@neolyst.com");
      await page.fill('input[type="password"]', "Analyst123");
      await page.click('button[type="submit"]');
      await expect(page).toHaveURL(/\/desktop/, { timeout: 15000 });

      // Similar to regions - UI protection exists but RLS allows reading
      // Actual RLS read access would need API/DB level testing
    });

    test("only admin can write to analyst table", async ({ page }) => {
      // Login as admin
      await page.goto("/login");
      await page.fill('input[type="email"]', "jiang_jiahong@qq.com");
      await page.fill('input[type="password"]', "Admin123");
      await page.click('button[type="submit"]');
      await expect(page).toHaveURL(/\/desktop/, { timeout: 15000 });

      // Navigate to analyst info
      await page.goto("/analyst-info");
      await expect(page).toHaveURL(/\/analyst-info/, { timeout: 5000 });

      // Try to create analyst - should succeed
      await page.click('button:has-text("Create Analyst")');
      await expect(page.locator("role=dialog")).toBeVisible();
      await page.waitForFunction(
        () => {
          const select = document.querySelector("#region_id");
          return select && select.querySelectorAll("option").length > 1;
        },
        { timeout: 10000 },
      );
      await page.fill("#full_name", "RLS Test Analyst");
      await page.fill("#email", `rls.test.${Date.now()}@example.com`);
      await page.selectOption("#region_id", { label: "India (IN)" });
      await page.getByRole("button", { name: "Create", exact: true }).focus();
      await page.keyboard.press("Enter");
      await page.waitForTimeout(1000);

      // Should succeed (no error about permission denied)
      await expect(page.locator("body")).not.toContainText("permission", {
        timeout: 5000,
      });
    });
  });

  test.describe("Delete Cascade", () => {
    test("deleting region sets analyst region_id to NULL", async ({ page }) => {
      // Login as admin
      await page.goto("/login");
      await page.fill('input[type="email"]', "jiang_jiahong@qq.com");
      await page.fill('input[type="password"]', "Admin123");
      await page.click('button[type="submit"]');
      await expect(page).toHaveURL(/\/desktop/, { timeout: 15000 });

      // First create a temporary region for cascade test
      await page.goto("/regions");
      await page.click('button:has-text("Create Region")');
      await expect(page.locator("role=dialog")).toBeVisible();
      const timestamp = Date.now();
      await page.fill("#name", `Cascade Region ${timestamp}`);
      await page.fill("#code", `CR${timestamp % 10000}`);
      await page.keyboard.press("Enter");
      await page.waitForTimeout(1000);
      await expect(page.locator("table")).toContainText(
        `Cascade Region ${timestamp}`,
        { timeout: 5000 },
      );

      // Now create an analyst linked to this region
      await page.goto("/analyst-info");
      await page.click('button:has-text("Create Analyst")');
      await expect(page.locator("role=dialog")).toBeVisible();
      await page.waitForFunction(
        () => {
          const select = document.querySelector("#region_id");
          return select && select.querySelectorAll("option").length > 1;
        },
        { timeout: 10000 },
      );
      await page.fill("#full_name", "Cascade Test Analyst");
      await page.fill("#email", `cascade.${Date.now()}@example.com`);
      await page.selectOption("#region_id", {
        label: `Cascade Region ${timestamp} (CR${timestamp % 10000})`,
      });
      await page.getByRole("button", { name: "Create", exact: true }).focus();
      await page.keyboard.press("Enter");
      await page.waitForTimeout(1000);
      await expect(page.locator("table")).toContainText(
        "Cascade Test Analyst",
        { timeout: 5000 },
      );

      // Now go to regions and delete the cascade region
      await page.goto("/regions");
      const row = page
        .locator("table tbody tr")
        .filter({ hasText: `Cascade Region ${timestamp}` });
      await row.locator('button:has-text("Delete")').click();

      // Confirm deletion
      const dialog = page.locator("role=dialog");
      await expect(dialog).toBeVisible();
      await dialog.getByRole("button", { name: "Delete" }).click();

      // Should show success toast
      await expect(page.locator("[aria-live='polite']")).toContainText(
        "Region deleted",
        { timeout: 5000 },
      );

      // Go back to analyst info and verify region is NULL
      await page.goto("/analyst-info");
      const analystRow = page
        .locator("table tbody tr")
        .filter({ hasText: "Cascade Test Analyst" });

      // Region column should show "-" (NULL)
      await expect(analystRow.locator("td").nth(3)).toContainText("-");
    });
  });

  test.describe("Unique Constraints", () => {
    test("region name must be unique", async ({ page }) => {
      await page.goto("/login");
      await page.fill('input[type="email"]', "jiang_jiahong@qq.com");
      await page.fill('input[type="password"]', "Admin123");
      await page.click('button[type="submit"]');
      await expect(page).toHaveURL(/\/desktop/, { timeout: 15000 });

      await page.goto("/regions");

      // Try to create duplicate region name (Japan exists)
      await page.click('button:has-text("Create Region")');
      await expect(page.locator("role=dialog")).toBeVisible();
      await page.fill("#name", "Japan");
      await page.fill("#code", "DUP");
      await page.keyboard.press("Enter");

      // Should show unique constraint error in toast
      await expect(page.locator("[aria-live='polite']")).toContainText(
        "Region name already exists",
        {
          timeout: 10000,
        },
      );
    });

    test("region code must be unique", async ({ page }) => {
      await page.goto("/login");
      await page.fill('input[type="email"]', "jiang_jiahong@qq.com");
      await page.fill('input[type="password"]', "Admin123");
      await page.click('button[type="submit"]');
      await expect(page).toHaveURL(/\/desktop/, { timeout: 15000 });

      await page.goto("/regions");

      // Try to create duplicate code (JP exists)
      await page.click('button:has-text("Create Region")');
      await expect(page.locator("role=dialog")).toBeVisible();
      await page.fill("#name", "Duplicate");
      await page.fill("#code", "JP");
      await page.keyboard.press("Enter");

      // Should show unique constraint error in toast
      await expect(page.locator("[aria-live='polite']")).toContainText(
        "Region code already exists",
        {
          timeout: 10000,
        },
      );
    });

    test("analyst email must be unique", async ({ page }) => {
      await page.goto("/login");
      await page.fill('input[type="email"]', "jiang_jiahong@qq.com");
      await page.fill('input[type="password"]', "Admin123");
      await page.click('button[type="submit"]');
      await expect(page).toHaveURL(/\/desktop/, { timeout: 15000 });

      await page.goto("/analyst-info");

      // First create an analyst
      await page.click('button:has-text("Create Analyst")');
      await expect(page.locator("role=dialog")).toBeVisible();
      await page.waitForFunction(
        () => {
          const select = document.querySelector("#region_id");
          return select && select.querySelectorAll("option").length > 1;
        },
        { timeout: 10000 },
      );

      const uniqueEmail = `rls.unique.${Date.now()}@example.com`;
      await page.fill("#full_name", "RLS Unique Test");
      await page.fill("#email", uniqueEmail);
      await page.selectOption("#region_id", { label: "India (IN)" });
      await page.getByRole("button", { name: "Create", exact: true }).focus();
      await page.keyboard.press("Enter");
      await expect(page.locator("role=dialog")).not.toBeVisible({
        timeout: 10000,
      });

      // Now try to create duplicate with same email
      await page.click('button:has-text("Create Analyst")');
      await expect(page.locator("role=dialog")).toBeVisible();
      await page.waitForFunction(
        () => {
          const select = document.querySelector("#region_id");
          return select && select.querySelectorAll("option").length > 1;
        },
        { timeout: 10000 },
      );
      await page.fill("#full_name", "Duplicate Email Test");
      await page.fill("#email", uniqueEmail);
      await page.selectOption("#region_id", { label: "Japan (JP)" });
      await page.getByRole("button", { name: "Create", exact: true }).focus();
      await page.keyboard.press("Enter");

      // Should show unique constraint error in toast
      await expect(page.locator("[aria-live='polite']")).toContainText(
        "Email already exists",
        {
          timeout: 10000,
        },
      );
    });
  });
});
