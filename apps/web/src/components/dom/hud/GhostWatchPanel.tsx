import { useCallback, useState } from 'react';
import { useGhostStore } from '../../../state/store';
import { MetricRow } from '../common/MetricRow';

import { API_BASE } from '../../../config/apiBase';

/** M12 — simulated rollout observation (SIMULATED_ROLLOUT). */
export function GhostWatchPanel() {
  const mode = useGhostStore((s) => s.mode);
  const ghostwatch = useGhostStore((s) => s.ghostwatch);
  const setGhostwatch = useGhostStore((s) => s.setGhostwatch);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const simulate = useCallback(async () => {
    setBusy(true);
    setErr(null);
    try {
      const r = await fetch(`${API_BASE}/v1/ghostwatch/simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario: 'good-canary' }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const body = (await r.json()) as {
        label: string;
        steps: { stage: string; analysis_outcome: string; campaign_state: string }[];
      };
      const last = body.steps[body.steps.length - 1];
      setGhostwatch({
        label: body.label,
        lastStage: last?.stage ?? '',
        lastOutcome: last?.analysis_outcome ?? '',
        campaignState: last?.campaign_state ?? '',
      });
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Simulate failed');
    } finally {
      setBusy(false);
    }
  }, [setGhostwatch]);

  if (mode !== 'evidence') return null;

  return (
    <section className="ghostwatch-panel" aria-label="GhostWatch rollout observation">
      <h2 className="a11y-heading">GhostWatch</h2>
      <p className="promotion-boundary-note">SIMULATED_ROLLOUT — not production</p>
      <button type="button" disabled={busy} onClick={() => void simulate()}>
        {busy ? 'Observing…' : 'SIMULATE CANARY'}
      </button>
      {err && <p role="alert">{err}</p>}
      {ghostwatch && (
        <>
          <MetricRow label="Environment" value={ghostwatch.label} />
          <MetricRow label="Stage" value={ghostwatch.lastStage} />
          <MetricRow label="Analysis" value={ghostwatch.lastOutcome} />
          <MetricRow label="Campaign" value={ghostwatch.campaignState} />
        </>
      )}
    </section>
  );
}
