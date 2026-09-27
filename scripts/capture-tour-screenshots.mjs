#!/usr/bin/env node
/** Tour screenshots — run with preview + fixture/tour mode. */
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const BASE = process.env.BASE_URL ?? 'http://127.0.0.1:4173';
const outDir = path.join('artifacts', 'screenshots', 'tour');

async function main() {
  const { chromium } = await import('playwright');
  await mkdir(outDir, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto(BASE);
  await page.evaluate(() => localStorage.removeItem('ghostrange.tour.completed'));
  await page.reload();
  await page.getByRole('button', { name: /4-minute tour/i }).click();
  await page.getByTestId('tour-build').click();
  await page.waitForSelector('.tour-callout', { timeout: 30000 });
  await page.screenshot({ path: path.join(outDir, '01-tour-welcome-running.png') });
  await browser.close();
  await writeFile(
    path.join(outDir, 'manifest.json'),
    JSON.stringify({ captured_at: new Date().toISOString(), count: 1 }, null, 2),
  );
  console.log('Wrote tour screenshot to', outDir);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
