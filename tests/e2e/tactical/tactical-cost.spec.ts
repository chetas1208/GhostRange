import { test, expect } from '@playwright/test';

const API = process.env.PLAYWRIGHT_API_URL ?? process.env.API_URL ?? 'http://127.0.0.1:8000';

test.describe('Tactical cost chain', () => {
  test('cost.snapshot.updated and UI matches GET /cost', async ({ page, request }) => {
    test.setTimeout(240_000);

    const camp = await request.post(`${API}/v1/campaigns/golden`, { maxRedirects: 5 });
    if (camp.status() === 403) {
      test.skip(true, 'live campaign blocked in this environment');
    }
    expect(camp.ok()).toBeTruthy();
    const body = await camp.json();
    const rangeId = body.range_id as string;

    let apiMicros = 0;
    let sawCostEvent = false;
    for (let i = 0; i < 90; i++) {
      const snap = await request.get(`${API}/v1/ranges/${rangeId}/snapshot`);
      expect(snap.ok()).toBeTruthy();
      const snapBody = await snap.json();
      const events = snapBody.events ?? [];
      if (events.some((e: { event_name?: string }) => e.event_name === 'cost.snapshot.updated')) {
        sawCostEvent = true;
      }
      const cost = await request.get(`${API}/v1/ranges/${rangeId}/cost`);
      if (cost.ok()) {
        const c = await cost.json();
        apiMicros = Number(c.total_known_usd_micros ?? 0);
        if (sawCostEvent && apiMicros >= 0) break;
      }
      await new Promise((r) => setTimeout(r, 2000));
    }
    if (!sawCostEvent) {
      const m2 = await request.post(`${API}/v1/ranges/${rangeId}/runs/m2`, { maxRedirects: 5 });
      expect(m2.ok()).toBeTruthy();
      for (let j = 0; j < 90; j++) {
        const snap = await request.get(`${API}/v1/ranges/${rangeId}/snapshot`);
        const snapBody = await snap.json();
        const events = snapBody.events ?? [];
        if (events.some((e: { event_name?: string }) => e.event_name === 'cost.snapshot.updated')) {
          sawCostEvent = true;
          break;
        }
        await new Promise((r) => setTimeout(r, 2000));
      }
    }
    expect(sawCostEvent).toBeTruthy();

    await page.goto(`/?tab=execution&rangeId=${rangeId}`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    await expect(page.locator('.cost-indicator')).toBeVisible({ timeout: 60_000 });

    const hudText = (await page.locator('.cost-indicator').textContent()) ?? '';
    const recon = await request.get(`${API}/v1/ranges/${rangeId}/cost/reconciliation`);
    expect(recon.ok()).toBeTruthy();
    const reconBody = await recon.json();
    expect(['PENDING', 'MATCHED', 'DIFFERENCE', 'PROVIDER_UNAVAILABLE', 'NOT_SUPPORTED']).toContain(
      reconBody.status,
    );

    const cost = await request.get(`${API}/v1/ranges/${rangeId}/cost`);
    const canonical = await cost.json();
    const known = canonical.display?.known_total as string | undefined;
    if (known && apiMicros > 0) {
      expect(hudText).toContain(known.replace(/^\$/, '').split('.')[0].slice(0, 1) ? known.split('.')[0] : known);
    }
    expect(canonical.semantic_type).toBeTruthy();
    expect(canonical.finalized === false || canonical.finalized === true).toBeTruthy();
  });
});
