import { expect, test } from '@playwright/test';
import { attachStrictConsole, startM20Campaign, waitTestState } from './helpers';

test('SSE reconnect preserves worker count (no duplicate materialization)', async ({ page, context }) => {
  attachStrictConsole(page);
  await page.goto('/');
  await startM20Campaign(page);
  await waitTestState(page, (s) => Number(s.lastEventSeq) >= 12, 300_000);

  const before = await page.evaluate(() => {
    const s = window.__GHOSTRANGE_TEST_STATE__?.();
    return {
      workers: s?.workerCount ?? 0,
      seq: s?.lastEventSeq ?? 0,
      ids: s?.workerCount,
    };
  });

  await context.setOffline(true);
  await page.waitForTimeout(1200);
  await context.setOffline(false);

  await waitTestState(page, (s) => s.sseStatus === 'open' || s.connection === 'LIVE', 120_000);

  const after = await page.evaluate(() => window.__GHOSTRANGE_TEST_STATE__?.());
  expect(Number(after?.workerCount)).toBeLessThanOrEqual(Math.max(1, Number(before.workers) + 1));
  expect(Number(after?.lastEventSeq)).toBeGreaterThanOrEqual(Number(before.seq));
});
