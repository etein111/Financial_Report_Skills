import { test, expect } from '@playwright/test';

// Test credentials
const ADMIN_EMAIL = 'admin@test.com';
const ADMIN_PASSWORD = 'admin123';

test.describe('Capture Screenshots for Prototype Archive', () => {
  test.beforeEach(async ({ page }) => {
    // Set viewport to standard desktop size
    page.setViewportSize({ width: 1920, height: 1080 });
  });

  test('01 - Login Page', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'screenshots/01-login-page.jpg', fullPage: true });
  });

  test('02 - Desktop Page (after login)', async ({ page }) => {
    await page.goto('/');

    // Fill in login form
    await page.fill('input[type="email"]', ADMIN_EMAIL);
    await page.fill('input[type="password"]', ADMIN_PASSWORD);

    // Click login button
    await page.click('button[type="submit"]');

    // Wait for navigation to desktop
    await page.waitForURL('/desktop', { timeout: 10000 });
    await page.waitForLoadState('networkidle');

    await page.screenshot({ path: 'screenshots/02-desktop.jpg', fullPage: true });
  });

  test('03 - Users Management Page', async ({ page, context }) => {
    // Login first
    await context.clearCookies();
    await page.goto('/');

    await page.fill('input[type="email"]', ADMIN_EMAIL);
    await page.fill('input[type="password"]', ADMIN_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL('/desktop', { timeout: 10000 });

    // Navigate to users page
    await page.goto('/users');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'screenshots/03-users-page.jpg', fullPage: true });
  });

  test('04 - Regions Management Page', async ({ page, context }) => {
    // Login first
    await context.clearCookies();
    await page.goto('/');

    await page.fill('input[type="email"]', ADMIN_EMAIL);
    await page.fill('input[type="password"]', ADMIN_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL('/desktop', { timeout: 10000 });

    // Navigate to regions page
    await page.goto('/regions');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'screenshots/04-regions-page.jpg', fullPage: true });
  });

  test('05 - Analyst Info Page', async ({ page, context }) => {
    // Login first
    await context.clearCookies();
    await page.goto('/');

    await page.fill('input[type="email"]', ADMIN_EMAIL);
    await page.fill('input[type="password"]', ADMIN_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL('/desktop', { timeout: 10000 });

    // Navigate to analyst info page
    await page.goto('/analyst-info');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'screenshots/05-analyst-info-page.jpg', fullPage: true });
  });

  test('06 - Coming Soon Page', async ({ page }) => {
    await page.goto('/coming-soon');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'screenshots/06-coming-soon.jpg', fullPage: true });
  });

  test('07 - Simple Login Page', async ({ page }) => {
    await page.goto('/simple-login');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'screenshots/07-simple-login.jpg', fullPage: true });
  });
});
