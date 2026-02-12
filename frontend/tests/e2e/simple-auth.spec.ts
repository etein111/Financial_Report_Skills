import { test, expect } from '@playwright/test';

test.describe('简单登录测试', () => {
  test('基本登录流程', async ({ page }) => {
    // 访问登录页面
    await page.goto('/login');

    // 等待页面加载（使用更可靠的方式）
    await page.waitForLoadState('domcontentloaded');

    // 等待输入框出现
    await page.waitForSelector('#email', { timeout: 10000 });

    // 输入登录凭据
    await page.fill('#email', 'admin@neolyst.com');
    await page.fill('#password', 'Admin123');

    // 点击登录按钮
    await page.click('button[type="submit"]');

    // 等待跳转完成（最长时间 15 秒）
    await page.waitForURL('**/desktop', { timeout: 15000 });

    // 验证我们在桌面页面
    expect(page.url()).toContain('/desktop');
  });
});
