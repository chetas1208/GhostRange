import { useCallback, useState } from 'react';
import { useGhostStore } from '../../../state/store';
import { MetricRow } from '../common/MetricRow';

import { API_BASE } from '../../../config/apiBase';

export function CausalPanel() {
  const mode = useGhostStore((s) => s.mode);
  const causal = useGhostStore((s) => s.causal);
  const setCausal = useGhostStore((s) => s.setCausal);
  const [busy, setBusy] = useState(false);

  const run = useCallback(async () => {
    setBusy(true);
    try {
      const r = await fetch(`${API_BASE}/v1/causal/demo/flagship`, { method: 'POST' });
      const body = (await r.json()) as Record<string, unknown>;
      setCausal({
        label: String(body.label ?? 'SIMULATED_SCM'),
        cacheBlocks: Boolean(body.cache_blocks_bypass),
        transportC: String(body.transport_C ?? ''),
        rejectsCTransport: Boolean(body.m14_rejects_C_transport),
      });
    } finally {
      setBusy(false);
    }
  }, [setCausal]);

  if (mode !== 'evidence') return null;

  return (
    <section aria-label="GhostCausal">
      <h2 className="a11y-heading">GhostCausal</h2>
      <p className="promotion-boundary-note">SIMULATED_SCM — not production intervention</p>
      <button type="button" disabled={busy} onClick={() => void run()}>
        RUN M14 FLAGSHIP
      </button>
      {causal && (
        <>
          <MetricRow label="Cache intervention blocks bypass" value={causal.cacheBlocks ? 'yes' : 'no'} />
          <MetricRow label="Transport to C" value={causal.transportC} />
          <MetricRow label="M14 rejects C (structural match)" value={causal.rejectsCTransport ? 'yes' : 'no'} />
        </>
      )}
    </section>
  );
}
