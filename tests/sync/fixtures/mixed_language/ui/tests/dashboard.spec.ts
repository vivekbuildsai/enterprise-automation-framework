import { test, expect } from '@playwright/test';

test('dashboard shows welcome message', async ({ page }) => {
  await page.goto('https://example.test/dashboard');
  await expect(page.locator('.welcome')).toBeVisible();
});
