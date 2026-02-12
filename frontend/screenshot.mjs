import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  try {
    console.log('Navigating to http://localhost:5173/login');
    await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle' });

    // 等待 5 秒让页面完全加载
    await page.waitForTimeout(5000);

    // 截图
    await page.screenshot({ path: 'screenshot.png', fullPage: true });
    console.log('Screenshot saved to screenshot.png');

    // 获取页面标题
    const title = await page.title();
    console.log('Page title:', title);

    // 捕获所有控制台消息
    page.on('console', msg => {
      console.log(`[${msg.type()}]`, msg.text());
    });

    // 捕获页面错误
    page.on('pageerror', error => {
      console.error('Page error:', error.message);
      console.error('Stack:', error.stack);
    });

    // 获取页面内容
    const content = await page.content();
    console.log('Page HTML length:', content.length);

  } catch (error) {
    console.error('Error:', error);
  } finally {
    await browser.close();
  }
})();
