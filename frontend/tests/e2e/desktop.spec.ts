import { test, expect } from '@playwright/test';

test.describe('桌面页面测试', () => {
  test.beforeEach(async ({ page }) => {
    // 登录
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    await page.fill('#email', 'admin@neolyst.com');
    await page.fill('#password', 'Admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/desktop', { timeout: 10000 });
  });

  test('显示欢迎信息和用户名', async ({ page }) => {
    // 验证欢迎信息
    await expect(page.locator('text=/Welcome, System Administrator/')).toBeVisible();
  });

  test('显示所有功能卡片', async ({ page }) => {
    // Reports 组卡片
    await expect(page.locator('text=Research Reports')).toBeVisible();
    await expect(page.locator('text=Sector Analysis')).toBeVisible();

    // Data Management 组卡片
    await expect(page.locator('text=Regions')).toBeVisible();
    await expect(page.locator('text=Analyst Information')).toBeVisible();
    await expect(page.locator('text=Users')).toBeVisible();
  });

  test('点击功能卡片在新标签页打开', async ({ page, context }) => {
    // 监听新页面
    const pagePromise = context.waitForEvent('page');

    // 点击 Regions 卡片
    await page.click('text=Regions');

    // 等待新标签页打开
    const newPage = await pagePromise;

    // 验证新页面 URL
    await expect(newPage).toHaveURL(/\/regions/);
  });

  test('点击 Logout 按钮登出', async ({ page }) => {
    // 点击 Logout 按钮
    await page.click('button:has-text("Logout")');

    // 验证重定向到登录页
    await page.waitForURL('/login', { timeout: 5000 });
    await expect(page).toHaveURL('/login');
  });
});
