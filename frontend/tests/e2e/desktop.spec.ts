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
    await expect(page.locator('.card-title:has-text("Reports")').first()).toBeVisible();
    await expect(page.locator('.card-title:has-text("New Report")')).toBeVisible();

    // Management 组卡片
    await expect(page.locator('.card-title:has-text("Regions")')).toBeVisible();
    await expect(page.locator('.card-title:has-text("Analyst Info")')).toBeVisible();
    await expect(page.locator('.card-title:has-text("Users")')).toBeVisible();
  });

  test('点击功能卡片导航到对应页面', async ({ page, context }) => {
    // 监听新标签页
    const pagePromise = context.waitForEvent('page');

    // 点击 Regions 卡片（使用更精确的选择器）
    await page.locator('.card:has-text("Regions")').click();

    // 等待新标签页打开
    const newPage = await pagePromise;
    await newPage.waitForLoadState('networkidle');

    // 验证新标签页显示 Regions 页面
    await expect(newPage.locator('h1:has-text("Regions")')).toBeVisible();
    await expect(newPage).toHaveURL(/\/regions/);

    // 关闭新标签页
    await newPage.close();
  });

  test('点击 Logout 按钮登出', async ({ page }) => {
    // 点击 Logout 按钮
    await page.click('button:has-text("Logout")');

    // 验证重定向到登录页
    await page.waitForURL('/login', { timeout: 5000 });
    await expect(page).toHaveURL('/login');
  });
});
