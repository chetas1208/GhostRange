#!/usr/bin/env node
/**
 * Capture 12 tactical UI screenshots from a LIVE backend (no injected store state).
 *
 * Usage:
 *   BASE_URL=http://45-76-248-45.nip.io API_URL=http://45-76-248-45.nip.io \
 *     node scripts/capture-tactical-ui.mjs
 */
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const BASE = process.env.BASE_URL ?? 'http://127.0.0.1:4173';
const API = process.env.API_URL ?? BASE;
const outDir = path.join('artifacts', 'screenshots', 'tactical');

async function waitForCostEvent(rangeId, timeoutMs = 180_000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    const snap = await fetch(`${API}/v1/ranges/${rangeId}/snapshot`);
    if (snap.ok) {
      const body = await snap.json();
      const events = body.events ?? [];
      if (events.some((e) => e.event_name === 'cost.snapshot.updated')) return body.sequence ?? 0;
      if ((body.sequence ?? 0) >= 8) return body.sequence ?? 0;
    }
    await new Promise((r) => setTimeout(r, 2000));
  }
  throw new Error('timeout waiting for campaign events / cost snapshot');
}

async function main() {
  const { chromium } = await import('playwright');
  const execPath = chromium.executablePath();
  await mkdir(outDir, { recursive: true });

  const campRes = await fetch(`${API}/v1/campaigns/golden`, { method: 'POST', redirect: 'follow' });
  if (!campRes.ok) {
    throw new Error(`campaign start failed: ${campRes.status} ${await campRes.text()}`);
  }
  const camp = await campRes.json();
  const rangeId = camp.range_id;
  const campaignId = camp.campaign?.campaign_id ?? camp.campaign_id ?? null;
  const seq = await waitForCostEvent(rangeId);

  const costRes = await fetch(`${API}/v1/ranges/${rangeId}/cost`);
  const costBody = costRes.ok ? await costRes.json() : null;
  const reconRes = await fetch(`${API}/v1/ranges/${rangeId}/cost/reconciliation`);
  const reconBody = reconRes.ok ? await reconRes.json() : null;

  const browser = await chromium.launch({
    executablePath: execPath,
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--mute-audio', '--disable-gpu'],
  });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  const manifest = [];
  const ts = new Date().toISOString();

  const shots = [
    ['01-multiverse-overview.png', `/?tab=multiverse&rangeId=${rangeId}`, 'MULTIVERSE'],
    ['02-multiverse-live-hud.png', `/?tab=multiverse&rangeId=${rangeId}`, 'MULTIVERSE'],
    ['03-execution-overview.png', `/?tab=execution&rangeId=${rangeId}`, 'EXECUTION'],
    ['04-execution-mission-strip.png', `/?tab=execution&rangeId=${rangeId}`, 'EXECUTION'],
    ['05-evidence-overview.png', `/?tab=evidence&rangeId=${rangeId}`, 'EVIDENCE'],
    ['06-evidence-inspector.png', `/?tab=evidence&rangeId=${rangeId}`, 'EVIDENCE'],
    ['07-cost-hud.png', `/?tab=execution&rangeId=${rangeId}`, 'EXECUTION'],
    ['08-environment-badge.png', `/?tab=multiverse&rangeId=${rangeId}`, 'MULTIVERSE'],
    ['09-event-ticker.png', `/?tab=execution&rangeId=${rangeId}`, 'EXECUTION'],
    ['10-three-tab-chrome.png', `/?tab=multiverse&rangeId=${rangeId}`, 'MULTIVERSE'],
    ['11-timing-api-ready.png', `/?tab=execution&rangeId=${rangeId}`, 'EXECUTION'],
    ['12-full-tactical-overview.png', `/?tab=execution&rangeId=${rangeId}`, 'EXECUTION'],
  ];

  for (const [file, route, tab] of shots) {
    await page.goto(`${BASE}${route}`, { waitUntil: 'networkidle', timeout: 120_000 });
    await page.waitForTimeout(2500);
    if (file === '07-cost-hud.png') {
      const costBtn = page.getByRole('button', { name: /COST/i });
      if (await costBtn.count()) await costBtn.first().click();
    }
    const fp = path.join(outDir, file);
    await page.screenshot({ path: fp, fullPage: false });
    manifest.push({
      file,
      route,
      tab,
      campaign_id: campaignId,
      range_id: rangeId,
      event_cursor: seq,
      mode: 'LIVE',
      timestamp: ts,
      backend_cost_micros: costBody?.total_known_usd_micros ?? null,
      reconciliation_status: reconBody?.status ?? null,
    });
  }

  await browser.close();
  await writeFile(
    path.join(outDir, 'manifest.json'),
    JSON.stringify({ captured_at: ts, base_url: BASE, api_url: API, shots: manifest }, null, 2),
  );
  console.log(`Wrote ${manifest.length} screenshots to ${outDir}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
