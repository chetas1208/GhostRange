import type { Page } from '@playwright/test';

const BENIGN_CONSOLE = [
  /favicon\.ico/i,
  /Download the React DevTools/i,
  /Failed to load resource: the server responded with a status of 404/i,
];

export function attachStrictConsole(page: Page) {
  const errors: string[] = [];
  page.on('pageerror', (err) => errors.push(`pageerror: ${err.message}`));
  page.on('console', (msg) => {
    if (msg.type() !== 'error') return;
    const text = msg.text();
    if (BENIGN_CONSOLE.some((re) => re.test(text))) return;
    errors.push(`console.error: ${text}`);
  });
  page.on('requestfailed', (req) => {
    const url = req.url();
    if (url.includes('/stream')) return;
    errors.push(`requestfailed: ${url} ${req.failure()?.errorText ?? ''}`);
  });
  return errors;
}

export async function waitTestState(
  page: Page,
  predicate: (s: Record<string, unknown>) => boolean,
  timeout = 240_000,
) {
  await page.waitForFunction(
    (fnBody) => {
      const read = (window as unknown as { __GHOSTRANGE_TEST_STATE__?: () => Record<string, unknown> })
        .__GHOSTRANGE_TEST_STATE__;
      if (!read) return false;
      const s = read();
      // eslint-disable-next-line no-new-func
      return new Function('s', `return (${fnBody})(s)`)(s);
    },
    predicate.toString(),
    { timeout },
  );
}

export async function waitMinEventSeq(page: Page, minSeq: number, timeout = 240_000) {
  await page.waitForFunction(
    (min) => {
      const s = (window as unknown as { __GHOSTRANGE_TEST_STATE__?: () => Record<string, unknown> })
        .__GHOSTRANGE_TEST_STATE__?.();
      return Boolean(s && Number(s.lastEventSeq) > min);
    },
    minSeq,
    { timeout },
  );
}

export async function waitForTestHook(page: Page) {
  await page.waitForFunction(
    () => typeof (window as unknown as { __GHOSTRANGE_TEST_STATE__?: unknown }).__GHOSTRANGE_TEST_STATE__ === 'function',
    { timeout: 60_000 },
  );
}

export async function startM20Campaign(page: Page) {
  await waitForTestHook(page);
  await page.keyboard.press('Control+KeyK');
  await page.getByRole('dialog', { name: 'Command surface' }).waitFor({ state: 'visible' });
  await page.getByTestId('start-m20-campaign').click();
  await waitTestState(
    page,
    (s) =>
      s.dataSource === 'live' &&
      (s.connection === 'LIVE' || s.sseStatus === 'open' || Number(s.lastEventSeq) >= 5),
    300_000,
  );
}

export async function setMode(page: Page, label: 'MULTIVERSE' | 'EXECUTION' | 'EVIDENCE') {
  await page.locator('.mode-selector button.mode-pill', { hasText: label }).click();
}
