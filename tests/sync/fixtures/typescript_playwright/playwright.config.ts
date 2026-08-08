import { defineConfig } from '@playwright/test';

export default defineConfig({
  retries: 2,
  workers: 4,
  reporter: [['html'], ['allure-playwright']],
  use: {
    browserName: 'chromium',
  },
});
