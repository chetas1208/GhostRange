import { expect, test } from '@playwright/test';
import { attachStrictConsole, setMode, startM20Campaign, waitMinEventSeq, waitTestState } from './helpers';

test.describe.configure({ mode: 'serial' });

test.describe('M20 golden path (live SSE)', () => {
  test('campaign stream drives three modes without console errors', async ({ page }) => {
    const errors = attachStrictConsole(page);
    await page.goto('/');
    await page.waitForSelector('.app-shell', { timeout: 60_000 });

    await startM20Campaign(page);

    await waitTestState(
      page,
      (s) => Boolean(s.hasActiveWorld) || Number(s.lastEventSeq) >= 8,
      300_000,
    );

    await setMode(page, 'MULTIVERSE');
    await waitTestState(page, (s) => s.mode === 'multiverse');

    await setMode(page, 'EXECUTION');
    await waitTestState(page, (s) => s.mode === 'execution');

    await waitTestState(
      page,
      (s) => Number(s.lastEventSeq) >= 12,
      300_000,
    );

    await setMode(page, 'EVIDENCE');
    await waitTestState(page, (s) => s.mode === 'evidence');

    for (let i = 0; i < 3; i++) {
      await setMode(page, 'MULTIVERSE');
      await setMode(page, 'EXECUTION');
      await setMode(page, 'EVIDENCE');
    }

    await expect(page.locator('#root')).not.toBeEmpty();

    await waitTestState(
      page,
      (s) => Number(s.workerCount) === 0 || s.campaignPhase === 'COMPLETED' || Number(s.lastEventSeq) >= 20,
      300_000,
    );

    expect(errors, errors.join('\n')).toEqual([]);
  });

  test('SSE receives durable events with advancing sequence', async ({ page }) => {
    attachStrictConsole(page);
    await page.goto('/');
    await startM20Campaign(page);
    const seqBefore = await page.evaluate(() => window.__GHOSTRANGE_TEST_STATE__?.().lastEventSeq ?? 0);
    await waitMinEventSeq(page, Number(seqBefore) + 5, 240_000);
    const st = await page.evaluate(() => window.__GHOSTRANGE_TEST_STATE__?.());
    expect(st?.sseStatus).toBe('open');
    expect(Number(st?.lastEventSeq)).toBeGreaterThan(5);
  });
});
