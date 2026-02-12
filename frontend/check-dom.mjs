import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  try {
    await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle' });

    // 等待 Vue 挂载
    await page.waitForTimeout(3000);

    // 检查 #app 元素的内容
    const appContent = await page.evaluate(() => {
      const app = document.getElementById('app');
      return app ? app.innerHTML : 'not found';
    });
    console.log('#app innerHTML:', appContent.substring(0, 500));

    // 检查页面的完整 HTML
    const bodyHTML = await page.evaluate(() => document.body.innerHTML);
    console.log('Body HTML length:', bodyHTML.length);

  } catch (error) {
    console.error('Error:', error);
  } finally {
    await browser.close();
  }
})();
