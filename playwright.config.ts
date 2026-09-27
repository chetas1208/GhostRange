import { defineConfig, devices } from '@playwright/test';
import { chromium } from 'playwright';

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:4173';

export default defineConfig({
  testDir: 'tests/e2e/ui-final',
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  timeout: 300_000,
  reporter: [
    ['list'],
    ['html', { outputFolder: 'artifacts/e2e/reports', open: 'never' }],
  ],
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
    launchOptions: {
      args: ['--no-sandbox', '--disable-dev-shm-usage', '--mute-audio', '--headless=old'],
    },
  },
  expect: {
    toHaveScreenshot: {
      maxDiffPixels: 800,
      animations: 'disabled',
    },
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        launchOptions: {
          executablePath: chromium.executablePath(),
          args: ['--no-sandbox', '--disable-dev-shm-usage', '--mute-audio', '--headless=new'],
        },
      },
    },
    {
      name: 'firefox-smoke',
      use: { ...devices['Desktop Firefox'] },
      testMatch: /smoke\.spec\.ts/,
    },
    {
      name: 'webkit-smoke',
      use: { ...devices['Desktop Safari'] },
      testMatch: /smoke\.spec\.ts/,
    },
    {
      name: 'reduced-motion',
      use: {
        ...devices['Desktop Chrome'],
        reducedMotion: 'reduce',
      },
      testMatch: /reduced-motion\.spec\.ts/,
    },
  ],
});
