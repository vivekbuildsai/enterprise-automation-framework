import { test, expect } from '@playwright/test';

test.describe('login', () => {
  test('valid login reaches secure area', { tag: '@smoke' }, async ({ page }) => {
    await page.goto('https://example.test/login');
    await page.fill('#username', 'demo_user');
    await page.fill('#password', 'demo_password');
    await page.click('#login');
    await expect(page.locator('h2')).toContainText('Secure Area');
  });

  test('invalid password shows error', { tag: '@regression' }, async ({ page }) => {
    await page.goto('https://example.test/login');
    await page.fill('#username', 'demo_user');
    await page.fill('#password', 'wrong_password');
    await page.click('#login');
    await expect(page.locator('.error')).toBeVisible();
  });
});
