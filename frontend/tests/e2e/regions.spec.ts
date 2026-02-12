import { test, expect } from '@playwright/test';

test.describe('Region 管理测试', () => {
  test.beforeEach(async ({ page }) => {
    // 登录
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    await page.fill('#email', 'admin@neolyst.com');
    await page.fill('#password', 'Admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/desktop', { timeout: 10000 });
  });

  test('查看 Region 列表', async ({ page }) => {
    await page.goto('/regions');

    // 等待页面加载
    await page.waitForLoadState('networkidle');

    // 验证页面标题
    await expect(page.locator('h1:has-text("Regions")')).toBeVisible();

    // 验证表格存在（如果有的话）
    const table = page.locator('.data-table');
    const isVisible = await table.isVisible();
    if (isVisible) {
      await expect(table).toBeVisible();
    }
  });

  test('创建新 Region', async ({ page }) => {
    await page.goto('/regions');
    await page.waitForLoadState('networkidle');

    // 获取创建前的数量
    const beforeCount = await page.locator('.data-table tbody tr').count();

    // 点击添加按钮
    await page.click('button:has-text("Add Region")');

    // 填写表单 - 使用 Math.random() 确保唯一性
    const randomId = Math.floor(Math.random() * 1000000);
    const regionName = `Test Region ${randomId}`;
    await page.fill('#name', regionName);
    await page.fill('#code', `TST${randomId}`);

    // 提交表单
    await page.click('button:has-text("Save")');

    // 等待对话框关闭（成功）或错误消息出现（失败）
    await Promise.race([
      page.waitForSelector('.dialog-overlay', { state: 'hidden', timeout: 5000 }),
      page.waitForSelector('.error-message', { state: 'visible', timeout: 5000 })
    ]);

    // 如果有错误，检查并抛出
    const errorElement = page.locator('.error-message').first();
    const hasError = await errorElement.isVisible();
    if (hasError) {
      const errorText = await errorElement.textContent();
      throw new Error(`创建 Region 失败: ${errorText}`);
    }

    // 等待表格更新
    await page.waitForTimeout(500);

    // 验证数量增加
    const afterCount = await page.locator('.data-table tbody tr').count();
    expect(afterCount).toBeGreaterThan(beforeCount);
  });

  test('编辑 Region', async ({ page }) => {
    await page.goto('/regions');

    // 点击第一个编辑按钮
    const editButton = page.locator('.btn-icon[title="Edit"]').first();
    const isVisible = await editButton.isVisible();

    if (isVisible) {
      await editButton.click();

      // 修改名称
      await page.fill('#name', 'Updated Region');

      // 提交表单
      await page.click('button:has-text("Save")');

      // 等待对话框关闭
      await page.waitForTimeout(1000);

      // 验证修改成功
      await expect(page.locator('text=Updated Region')).toBeVisible();
    }
  });

  test('删除 Region', async ({ page }) => {
    await page.goto('/regions');

    // 获取删除前的区域数量
    const initialCount = await page.locator('.data-table tbody tr').count();

    if (initialCount > 0) {
      // 点击第一个删除按钮
      await page.locator('.btn-icon.btn-danger[title="Delete"]').first().click();

      // 确认删除
      await page.click('button:has-text("Delete")');

      // 等待删除完成
      await page.waitForTimeout(1000);

      // 验证删除成功（数量减少）
      const finalCount = await page.locator('.data-table tbody tr').count();
      expect(finalCount).toBeLessThan(initialCount);
    }
  });
});
