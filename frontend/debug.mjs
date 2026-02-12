import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const consoleMessages = [];
  const errors = [];

  // 捕获所有控制台消息
  page.on('console', msg => {
    const text = msg.text();
    const type = msg.type();
    consoleMessages.push({ type, text });
    console.log(`[${type}]`, text);
  });

  // 捕获页面错误
  page.on('pageerror', error => {
    errors.push({ message: error.message, stack: error.stack });
    console.error('Page Error:', error.message);
    console.error('Stack:', error.stack);
  });

  // 捕获请求失败
  page.on('requestfailed', request => {
    console.error('Request Failed:', request.url(), request.failure().errorText);
  });

  try {
    console.log('Navigating to http://localhost:5173/login');
    await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle', timeout: 30000 });

    // 等待 10 秒
    await page.waitForTimeout(10000);

    // 截图
    await page.screenshot({ path: 'screenshot.png', fullPage: true });
    console.log('\n=== Console Messages Summary ===');
    console.log('Total messages:', consoleMessages.length);
    console.log('Errors:', errors.length);
    if (errors.length > 0) {
      console.error('\n=== Errors ===');
      errors.forEach((err, i) => {
        console.error(`${i + 1}.`, err.message);
        console.error('   Stack:', err.stack);
      });
    }

  } catch (error) {
    console.error('Navigation Error:', error);
  } finally {
    await browser.close();
  }
})();
