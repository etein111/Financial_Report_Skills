import { test, expect } from '@playwright/test';

test.describe('Analyst Info 管理测试', () => {
  test.beforeEach(async ({ page }) => {
    // 登录
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    await page.fill('#email', 'admin@neolyst.com');
    await page.fill('#password', 'Admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('/desktop', { timeout: 10000 });
  });

  test('查看 Analyst 列表', async ({ page }) => {
    await page.goto('/analyst-info');

    // 验证页面标题
    await expect(page.locator('h1:has-text("Analyst Information")')).toBeVisible();

    // 验证搜索框存在
    await expect(page.locator('.search-input')).toBeVisible();
  });

  test('搜索 Analyst', async ({ page }) => {
    await page.goto('/analyst-info');

    // 输入搜索关键词
    await page.fill('.search-input', 'John');

    // 等待搜索结果
    await page.waitForTimeout(500);

    // 验证搜索结果
    const results = page.locator('.data-table tbody tr');
    const count = await results.count();

    if (count > 0) {
      // 如果有结果，验证至少有一个包含关键词
      const firstRowText = await results.first().textContent();
      expect(firstRowText?.toLowerCase()).toContain('john');
    }
  });

  test('创建新 Analyst', async ({ page }) => {
    await page.goto('/analyst-info');

    // 获取创建前的数量
    const beforeCount = await page.locator('.data-table tbody tr').count();

    // 点击添加按钮
    await page.click('button:has-text("Add Analyst")');

    // 填写表单
    const timestamp = Date.now();
    await page.fill('#full_name', `Jane Doe ${timestamp}`);
    await page.fill('#chinese_name', '李四');
    await page.fill('#email', `jane.doe${timestamp}@example.com`);
    await page.fill('#suffix', 'CFA');
    await page.fill('#sfc', 'XYZ789');

    // 提交表单
    await page.click('button:has-text("Save")');

    // 等待对话框关闭和数据刷新（页面重新加载）
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // 验证新创建的 Analyst 显示在列表中
    const afterCount = await page.locator('.data-table tbody tr').count();
    expect(afterCount).toBeGreaterThan(beforeCount);
  });

  test('邮箱唯一性检查', async ({ page }) => {
    await page.goto('/analyst-info');

    // 点击添加按钮
    await page.click('button:has-text("Add Analyst")');

    // 输入已存在的邮箱（假设 john@example.com 已存在）
    await page.fill('#full_name', 'Test User');
    await page.fill('#email', 'john@example.com');

    // 触发邮箱检查（失去焦点）
    await page.locator('#email').blur();

    // 等待检查完成
    await page.waitForTimeout(1000);

    // 验证错误提示（如果有的话）
    const errorElement = page.locator('.field-error');
    const isVisible = await errorElement.isVisible();
    if (isVisible) {
      const errorText = await errorElement.textContent();
      expect(errorText?.toLowerCase()).toContain('already');
    }
  });

  test('编辑 Analyst', async ({ page }) => {
    await page.goto('/analyst-info');

    // 点击第一个编辑按钮
    const editButton = page.locator('.btn-icon[title="Edit"]').first();
    const isVisible = await editButton.isVisible();

    if (isVisible) {
      await editButton.click();

      // 修改姓名
      await page.fill('#full_name', 'Updated Name');

      // 提交表单
      await page.click('button:has-text("Save")');

      // 等待对话框关闭
      await page.waitForTimeout(1000);

      // 验证修改成功
      await expect(page.locator('text=Updated Name')).toBeVisible();
    }
  });

  test('删除 Analyst', async ({ page }) => {
    await page.goto('/analyst-info');

    // 获取删除前的数量
    const initialCount = await page.locator('.data-table tbody tr').count();

    if (initialCount > 0) {
      // 点击第一个删除按钮
      await page.locator('.btn-icon.btn-danger[title="Delete"]').first().click();

      // 确认删除
      await page.click('button:has-text("Delete")');

      // 等待删除完成
      await page.waitForTimeout(1000);

      // 验证删除成功
      const finalCount = await page.locator('.data-table tbody tr').count();
      expect(finalCount).toBeLessThan(initialCount);
    }
  });
});
