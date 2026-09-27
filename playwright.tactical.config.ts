import { defineConfig, devices } from '@playwright/test';
import { chromium } from 'playwright';

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:4173';

export default defineConfig({
  testDir: 'tests/e2e/tactical',
  fullyParallel: false,
  workers: 1,
  timeout: 300_000,
  use: {
    baseURL,
    trace: 'retain-on-failure',
    viewport: { width: 1920, height: 1080 },
    launchOptions: {
      executablePath: chromium.executablePath(),
      args: ['--no-sandbox', '--disable-dev-shm-usage', '--mute-audio'],
    },
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
