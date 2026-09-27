#!/usr/bin/env node
/** Collect lightweight perf metrics during live golden path (Chromium CDP). */
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:4173/';
const out = process.argv[2] ?? path.join('artifacts', 'performance', 'm20-ui-performance.json');

const browser = await chromium.launch({
  executablePath: chromium.executablePath(),
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--mute-audio'],
});
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const client = await page.context().newCDPSession(page);
await client.send('Performance.enable');

await page.goto(baseURL, { waitUntil: 'domcontentloaded' });
await page.keyboard.press('Control+KeyK');
await page.getByTestId('start-m20-campaign').click();
await page.waitForFunction(
  () => {
    const s = window.__GHOSTRANGE_TEST_STATE__?.();
    return s && s.connection === 'LIVE' && Number(s.lastEventSeq) >= 15;
  },
  { timeout: 300_000 },
);

const samples = [];
for (let i = 0; i < 8; i++) {
  const m = await client.send('Performance.getMetrics');
  samples.push(Object.fromEntries(m.metrics.map((x) => [x.name, x.value])));
  await page.waitForTimeout(500);
}

const heap = await page.evaluate(() => {
  // @ts-expect-error perf memory optional
  const mem = performance.memory;
  return mem
    ? { usedJSHeapSize: mem.usedJSHeapSize, totalJSHeapSize: mem.totalJSHeapSize }
    : null;
});

const report = {
  captured_at: new Date().toISOString(),
  baseURL,
  samples,
  heap,
  test_state: await page.evaluate(() => window.__GHOSTRANGE_TEST_STATE__?.()),
  notes: 'FPS/draw calls require R3F profiler hook; metrics are Chromium Performance domain samples.',
};

fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, JSON.stringify(report, null, 2));
await browser.close();
console.log('Wrote', out);
