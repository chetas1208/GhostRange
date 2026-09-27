#!/usr/bin/env node
/** API-only release evidence (no browser) — cost, timing, events for one M20 campaign. */
const API = process.env.API_URL ?? 'http://45-76-248-45.nip.io';
const out = 'artifacts/release-evidence';

import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

async function main() {
  await mkdir(out, { recursive: true });
  const t0 = Date.now();
  const camp = await fetch(`${API}/v1/campaigns/golden`, { method: 'POST', redirect: 'follow' });
  const campBody = await camp.json();
  if (!camp.ok) throw new Error(`campaign ${camp.status}: ${JSON.stringify(campBody)}`);
  const rangeId = campBody.range_id;
  let seq = 0;
  let costEvent = false;
  for (let i = 0; i < 120; i++) {
    const snap = await fetch(`${API}/v1/ranges/${rangeId}/snapshot`);
    const body = await snap.json();
    seq = body.sequence ?? 0;
    if ((body.events ?? []).some((e) => e.event_name === 'cost.snapshot.updated')) costEvent = true;
    if (costEvent && seq >= 10) break;
    await new Promise((r) => setTimeout(r, 2000));
  }
  const cost = await (await fetch(`${API}/v1/ranges/${rangeId}/cost`)).json();
  const recon = await (await fetch(`${API}/v1/ranges/${rangeId}/cost/reconciliation`)).json();
  const timing = await (await fetch(`${API}/v1/ranges/${rangeId}/timing`)).json();
  const snap = await (await fetch(`${API}/v1/ranges/${rangeId}/snapshot`)).json();
  const report = {
    captured_at: new Date().toISOString(),
    api_url: API,
    elapsed_ms: Date.now() - t0,
    campaign: campBody,
    range_id: rangeId,
    event_sequence: seq,
    cost_snapshot_event: costEvent,
    cost,
    reconciliation: recon,
    timing,
    event_names: [...new Set((snap.events ?? []).map((e) => e.event_name))].sort(),
  };
  await writeFile(path.join(out, 'm20-live-campaign.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ ok: true, range_id: rangeId, costEvent, total_micros: cost.total_known_usd_micros }, null, 2));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
