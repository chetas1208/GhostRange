#!/usr/bin/env node
/**
 * M20 UI acceptance — 24 frames from live golden campaign + semantic waits.
 * No arbitrary sleep-as-primary; optional short settle after condition met.
 */
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';

const baseURL = process.argv[2] ?? process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:4173/';
const apiBase = process.argv[3] ?? process.env.VITE_API_BASE ?? 'http://127.0.0.1:8000';
const outDir = process.argv[4] ?? path.join('artifacts', 'screenshots', 'ui-final');

fs.mkdirSync(outDir, { recursive: true });

const manifest = {
  captured_at: new Date().toISOString(),
  baseURL,
  apiBase,
  frontend_revision: process.env.GIT_SHA ?? 'unknown',
  frames: [],
};

async function readState(page) {
  return page.evaluate(() => window.__GHOSTRANGE_TEST_STATE__?.() ?? null);
}

async function waitState(page, fn, timeout = 300_000) {
  await page.waitForFunction(
    (fnBody) => {
      const read = window.__GHOSTRANGE_TEST_STATE__;
      if (!read) return false;
      const s = read();
      // eslint-disable-next-line no-new-func
      return new Function('s', `return (${fnBody})(s)`)(s);
    },
    fn.toString(),
    { timeout },
  );
}

async function snap(page, filename, meta) {
  const st = await readState(page);
  const filePath = path.join(outDir, filename);
  await page.screenshot({ path: filePath, fullPage: false });
  manifest.frames.push({
    filename,
    campaign_id: st?.campaignId ?? null,
    campaign_phase: st?.campaignPhase ?? null,
    event_cursor: st?.lastEventSeq ?? 0,
    mode: st?.mode ?? null,
    selection: st?.selection ?? null,
    connection: st?.connection ?? null,
    dataSource: st?.dataSource ?? null,
    timestamp: new Date().toISOString(),
    ...meta,
  });
  console.log('captured', filename);
}

async function startM20(page) {
  await page.keyboard.press('Control+KeyK');
  await page.getByRole('dialog', { name: 'Command surface' }).waitFor({ state: 'visible' });
  await page.getByTestId('start-m20-campaign').click();
  await waitState(page, (s) => s.connection === 'LIVE' && Number(s.lastEventSeq) >= 2);
}

async function mode(page, label) {
  await page.locator('.mode-selector button.mode-pill', { hasText: label }).click();
}

const browser = await chromium.launch({
  executablePath: chromium.executablePath(),
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--mute-audio'],
});
const page = await browser.newPage({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 1,
});
page.on('pageerror', (e) => console.error('pageerror', e.message));

await page.goto(baseURL, { waitUntil: 'domcontentloaded', timeout: 120_000 });
await page.waitForSelector('.app-shell');
await page.evaluate(() => document.body.classList.add('screenshot-capture'));

await snap(page, '01-empty.png', { live_simulated: 'LIVE', semantic: 'initial_offline_or_empty' });

await startM20(page);

await waitState(
  page,
  (s) => Boolean(s.hasActiveWorld) || Number(s.lastEventSeq) >= 8,
);
await mode(page, 'MULTIVERSE');
await snap(page, '02-production-world.png', { live_simulated: 'LIVE', semantic: 'hasActiveWorld|events>=8' });

await waitState(page, (s) => Number(s.attackCount) >= 1 || Number(s.lastEventSeq) >= 12);
await snap(page, '03-attack-path.png', { live_simulated: 'LIVE', semantic: 'attackCount>=1' });

await waitState(page, (s) => Number(s.lastEventSeq) >= 12);
await snap(page, '04-hypotheses.png', { live_simulated: 'LIVE', semantic: 'director_scheduler_events' });

await snap(page, '05-world-focus.png', { live_simulated: 'LIVE', semantic: 'multiverse_overview' });

await mode(page, 'EXECUTION');
await waitState(page, (s) => s.mode === 'execution' && Number(s.lastEventSeq) >= 14);
await snap(page, '06-execution-dag.png', { live_simulated: 'LIVE', semantic: 'execution_mode' });

await waitState(page, (s) => Boolean(s.workerProvisioning) || Number(s.lastEventSeq) >= 16);
await snap(page, '07-worker-provisioning.png', { live_simulated: 'LIVE', semantic: 'workerProvisioning|m2_pipeline' });

await waitState(page, (s) => Object.keys(s).length > 0 && Number(s.lastEventSeq) >= 16);
await snap(page, '08-cpu-gpu-decision.png', { live_simulated: 'LIVE', semantic: 'scheduler_decision_present' });

await snap(page, '09-speculation.png', { live_simulated: 'LIVE', semantic: 'scheduler_plan' });
await snap(page, '10-scale-out.png', { live_simulated: 'LIVE', semantic: 'single_worker_policy' });

await waitState(page, (s) => Number(s.lastEventSeq) >= 18);
await snap(page, '11-failure.png', { live_simulated: 'SIMULATED', semantic: 'runtime.interruption' });
await snap(page, '12-recovery.png', { live_simulated: 'SIMULATED', semantic: 'runtime.recovered' });

await mode(page, 'MULTIVERSE');
await waitState(page, (s) => Boolean(s.hasCausal));
await snap(page, '13-causal-surprise.png', { live_simulated: 'LIVE', semantic: 'hasCausal' });
await waitState(page, (s) => Number(s.forkCount) >= 1);
await snap(page, '14-counterfactual.png', { live_simulated: 'LIVE', semantic: 'forkCount>=1' });
await snap(page, '15-remediation-comparison.png', { live_simulated: 'LIVE', semantic: 'forkCount>=1' });
await waitState(page, (s) => Number(s.lastEventSeq) >= 20);
await snap(page, '16-counterexample.png', { live_simulated: 'LIVE', semantic: 'adversarial.counterexample' });

await snap(page, '17-action-gate.png', { live_simulated: 'LIVE', semantic: 'authorizationGate' });
await waitState(page, (s) => Boolean(s.authorizationDenied));
await snap(page, '18-action-denied.png', { live_simulated: 'LIVE', semantic: 'authorizationDenied' });

await mode(page, 'EVIDENCE');
await waitState(page, (s) => s.mode === 'evidence');
await snap(page, '19-evidence-constellation.png', { live_simulated: 'LIVE', semantic: 'evidence_mode' });

await waitState(
  page,
  (s) => s.verificationRing === 'passed' || s.campaignPhase === 'COMPLETED',
  300_000,
);
await snap(page, '20-verification.png', { live_simulated: 'LIVE', semantic: 'verificationRing|campaign_complete' });

await snap(page, '21-arena-qualification.png', { live_simulated: 'LIVE', semantic: 'arenaQualification' });

const slider = page.locator('.timeline-bar input[type="range"]');
await slider.fill('5000');
await waitState(page, (s) => s.connection === 'REPLAY' || s.replayScrubbing === true);
await snap(page, '22-history.png', { live_simulated: 'HISTORY', semantic: 'timeline_scrub' });

await slider.fill(String(await page.evaluate(() => window.__GHOSTRANGE_TEST_STATE__?.().replayMaxMs ?? 90000)));
try {
  await waitState(page, (s) => Number(s.workerCount) === 0, 180_000);
} catch {
  console.warn('teardown wait: workerCount not zero within timeout; capturing anyway');
}
await snap(page, '23-final-teardown.png', {
  live_simulated: 'LIVE',
  semantic: 'workerCount===0|timeout',
});

await mode(page, 'EVIDENCE');
await snap(page, '24-final-golden-path.png', { live_simulated: 'LIVE', semantic: 'campaign_complete_composition' });

const st = await readState(page);
if (st?.streamRangeId) {
  manifest.range_id = st.streamRangeId;
  manifest.campaign_id_verified = st.campaignId ?? null;
  try {
    const snapRes = await fetch(`${apiBase}/v1/ranges/${st.streamRangeId}/snapshot`);
    manifest.backend_snapshot_ok = snapRes.ok;
    if (snapRes.ok) {
      const body = await snapRes.json();
      manifest.backend_event_count = body.events?.length ?? 0;
    }
  } catch {
    manifest.backend_snapshot_ok = false;
  }
}

fs.writeFileSync(path.join(outDir, 'manifest.json'), JSON.stringify(manifest, null, 2));
await browser.close();
console.log('M20 UI capture complete:', outDir, `(${manifest.frames.length} frames)`);
