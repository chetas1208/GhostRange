import { chromium } from 'playwright';
import path from 'node:path';
import fs from 'node:fs';

const url = process.argv[2] ?? 'http://127.0.0.1:4173/';
const outDir = process.argv[3] ?? path.join('artifacts', 'screenshots', 'm2');

fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch({
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--mute-audio'],
});
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.on('pageerror', (err) => console.error('pageerror:', err.message));
await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60_000 });
await page.waitForSelector('.timeline-bar input[type="range"]', { state: 'attached', timeout: 90_000 });
await page.waitForFunction(
  () => {
    const el = document.querySelector('.timeline-bar input[type="range"]');
    return el && Number(el.max) > 0;
  },
  { timeout: 90_000 },
);

const slider = page.locator('.timeline-bar input[type="range"]');
const snap = async (name) => {
  await page.screenshot({ path: path.join(outDir, name), fullPage: false });
};

const mode = async (label) => {
  const btn = page.locator('.mode-selector button.mode-pill', { hasText: label });
  await btn.click();
  await page.waitForTimeout(600);
};

const seek = async (ms) => {
  await slider.fill(String(ms));
  await page.waitForTimeout(700);
};

// Scrub pauses auto-replay; rewind to t=0 for empty chamber
await page.waitForTimeout(800);
await seek(0);
await page.waitForTimeout(300);
await snap('01-multiverse-empty.png');

await seek(2500);
await snap('02-multiverse-provisioning.png');

await seek(9000);
await snap('03-multiverse-ready.png');

await seek(16500);
await snap('04-multiverse-attack-active.png');

await mode('MULTIVERSE');
await seek(15100);
await snap('05-multiverse-world-fork.png');

await mode('EXECUTION');
await seek(12000);
await snap('06-execution-dag.png');

await seek(7000);
await snap('07-execution-provisioning-worker.png');

await seek(14000);
await snap('08-execution-speculative-split.png');

await mode('EVIDENCE');
await seek(22000);
await snap('09-evidence-unverified-claim.png');

await seek(26000);
await snap('10-evidence-verified-claim.png');

await mode('MULTIVERSE');
await seek(31000);
await snap('11-teardown-in-progress.png');

await seek(32000);
await snap('12-world-destroyed-history.png');

await browser.close();
console.log('Captured 12 acceptance screenshots in', outDir);
