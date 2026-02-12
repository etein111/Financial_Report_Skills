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

    // 验证页面标题
    await expect(page.locator('h1:has-text("Regions")')).toBeVisible();

    // 验证表格存在
    await expect(page.locator('.data-table')).toBeVisible();
  });

  test('创建新 Region', async ({ page }) => {
    await page.goto('/regions');

    // 点击添加按钮
    await page.click('button:has-text("Add Region")');

    // 填写表单
    await page.fill('#name', `Test Region ${Date.now()}`);
    await page.fill('#code', `TST${Date.now()}`);

    // 提交表单
    await page.click('button:has-text("Save")');

    // 等待对话框关闭（可能需要短暂的加载时间）
    await page.waitForTimeout(1000);

    // 验证新创建的 Region 显示在列表中
    await expect(page.locator('text=/Test Region/')).toBeVisible();
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
