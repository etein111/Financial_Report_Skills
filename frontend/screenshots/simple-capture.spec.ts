import { test, expect } from '@playwright/test';

// Admin credentials
const ADMIN_EMAIL = 'admin@test.com';
const ADMIN_PASSWORD = 'admin123';

test.describe('Screenshot Capture', () => {
  test.use({ viewport: { width: 1920, height: 1080 } });

  test('01 - Login Page', async ({ page }) => {
    await page.goto('http://localhost:8082/');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'screenshots/01-login-page.jpg', fullPage: true });
  });

  test('02 - Desktop Page', async ({ page, context }) => {
    // Set auth token directly (bypass API)
    await context.addInitScript(() => {
      localStorage.setItem('auth_token', 'mock-token-for-screenshot');
      localStorage.setItem('user_info', JSON.stringify({
        id: 'admin-id',
        email: 'admin@test.com',
        role: 'admin'
      }));
    });

    await page.goto('http://localhost:8082/desktop');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'screenshots/02-desktop.jpg', fullPage: true });
  });

  test('03 - Users Page', async ({ page, context }) => {
    await context.addInitScript(() => {
      localStorage.setItem('auth_token', 'mock-token');
      localStorage.setItem('user_info', JSON.stringify({ role: 'admin' }));
    });
    await page.goto('http://localhost:8082/users');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'screenshots/03-users-page.jpg', fullPage: true });
  });

  test('04 - Regions Page', async ({ page, context }) => {
    await context.addInitScript(() => {
      localStorage.setItem('auth_token', 'mock-token');
      localStorage.setItem('user_info', JSON.stringify({ role: 'admin' }));
    });
    await page.goto('http://localhost:8082/regions');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'screenshots/04-regions-page.jpg', fullPage: true });
  });

  test('05 - Analyst Info Page', async ({ page, context }) => {
    await context.addInitScript(() => {
      localStorage.setItem('auth_token', 'mock-token');
      localStorage.setItem('user_info', JSON.stringify({ role: 'admin' }));
    });
    await page.goto('http://localhost:8082/analyst-info');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'screenshots/05-analyst-info-page.jpg', fullPage: true });
  });

  test('06 - Coming Soon', async ({ page }) => {
    await page.goto('http://localhost:8082/coming-soon');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'screenshots/06-coming-soon.jpg', fullPage: true });
  });

  test('07 - Simple Login', async ({ page }) => {
    await page.goto('http://localhost:8082/simple-login');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'screenshots/07-simple-login.jpg', fullPage: true });
  });
});
