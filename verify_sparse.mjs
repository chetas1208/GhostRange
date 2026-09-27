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

// Let the fixture replay run forward briefly so the store has real data to
// seek within (the seek() call needs the replayer's event list ready).
await page.waitForTimeout(2000);

// Scrub to t=24s: world.ready + all 3 forks + 1 live compute worker + tasks
// running + (close to) evidence.created have all fired by then (per the m2
// fixture's offsets), and it's before compute.released/world.destroyed at
// 30-32s. seek() pauses playback, so all three tabs screenshot the same
// stable sparse moment.
async function seekTo(ms) {
  const input = page.locator('input[aria-label="Temporal rail"]');
  await input.evaluate((el, value) => {
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(el, String(value));
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  }, ms);
}

await seekTo(24000);
await page.waitForTimeout(800);
await page.screenshot({ path: '/tmp/gr-multiverse.png' });

async function clickMode(label) {
  const button = page.locator('button.mode').filter({ hasText: label }).first();
  if (!(await button.count())) return false;
  try {
    await button.click({ timeout: 2000 });
    return true;
  } catch {
    return false;
  }
}

const clickedExec = await clickMode('EXECUTE');
await page.waitForTimeout(800);
await page.screenshot({ path: '/tmp/gr-execution.png' });

const clickedEvidence = await clickMode('EVIDENCE');
await page.waitForTimeout(800);
await page.screenshot({ path: '/tmp/gr-evidence.png' });

// Also capture the true zero/near-zero-node moment (t=0, before anything
// has materialized) for the Multiverse tab, to see the emptiest real state.
await clickMode('WORLD');
await seekTo(500);
await page.waitForTimeout(800);
await page.screenshot({ path: '/tmp/gr-multiverse-empty.png' });

console.log(JSON.stringify({ clickedExec, clickedEvidence }));

await browser.close();
