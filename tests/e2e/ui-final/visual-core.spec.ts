import { expect, test } from '@playwright/test';
import { attachStrictConsole, setMode, startM20Campaign, waitTestState } from './helpers';

test.describe('visual regression (canonical chromium)', () => {
  test('live multiverse after world ready', async ({ page }) => {
    attachStrictConsole(page);
    await page.goto('/');
    await startM20Campaign(page);
    await waitTestState(
      page,
      (s) => Boolean(s.hasActiveWorld) || Number(s.lastEventSeq) >= 10,
      300_000,
    );
    await setMode(page, 'MULTIVERSE');
    await page.evaluate(() => document.body.classList.add('screenshot-capture'));
    await expect(page).toHaveScreenshot('02-production-world.png', {
      fullPage: false,
    });
  });

  test('execution mode DAG region', async ({ page }) => {
    attachStrictConsole(page);
    await page.goto('/');
    await startM20Campaign(page);
    await waitTestState(page, (s) => Number(s.lastEventSeq) >= 15, 300_000);
    await setMode(page, 'EXECUTION');
    await waitTestState(page, (s) => s.mode === 'execution');
    await page.evaluate(() => document.body.classList.add('screenshot-capture'));
    await expect(page).toHaveScreenshot('06-execution-dag.png', {
      fullPage: false,
    });
  });
});
