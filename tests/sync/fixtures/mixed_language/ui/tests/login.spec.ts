import { test, expect } from '@playwright/test';

test('valid login reaches secure area', async ({ page }) => {
  await page.goto('https://example.test/login');
  await page.fill('#username', 'demo_user');
  await page.click('#login');
  await expect(page.locator('h2')).toContainText('Secure Area');
});
