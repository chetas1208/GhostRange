import { chromium } from 'playwright';

const url = 'http://localhost:5183/';

const browser = await chromium.launch({
  executablePath: '/home/923873155/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome',
  args: ['--no-sandbox'],
});
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
page.on('console', (msg) => {
  if (msg.type() === 'error') console.log('PAGE ERROR:', msg.text());
});
page.on('pageerror', (err) => console.log('PAGE EXCEPTION:', err.message));

await page.goto(url, { waitUntil: 'networkidle' });

// Dismiss the welcome/tour modal so the canvas is unobstructed.
const exploreBtn = page.locator('text=Explore on my own').first();
if (await exploreBtn.count()) {
  await exploreBtn.click({ timeout: 3000 }).catch(() => {});
}
await page.waitForTimeout(500);

// Let the fixture replayer run forward so the sparse world/worker/task data
// actually materializes (m2 fixture: 1 world + 3 forks + 1 compute worker).
await page.waitForTimeout(8000);
await page.screenshot({ path: '/tmp/gr-multiverse.png' });

// Try to switch to Execution / Evidence via keyboard shortcuts / mode dock if present.
async function clickText(text) {
  const el = page.locator(`text=${text}`).first();
  if (await el.count()) {
    await el.click({ timeout: 2000 }).catch(() => {});
    return true;
  }
  return false;
}

const clickedExec = await clickText('EXECUTE');
await page.waitForTimeout(2500);
await page.screenshot({ path: '/tmp/gr-execution.png' });

const clickedEvidence = await clickText('EVIDENCE');
await page.waitForTimeout(2500);
await page.screenshot({ path: '/tmp/gr-evidence.png' });

console.log(JSON.stringify({ clickedExec, clickedEvidence }));

await browser.close();
