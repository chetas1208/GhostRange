import { useCallback, useState } from 'react';
import { useGhostStore } from '../../../state/store';
import { MetricRow } from '../common/MetricRow';

import { API_BASE } from '../../../config/apiBase';

/** M13 — federated defensive priors (SIMULATED_MESH). Evidence tab only. */
export function MeshPanel() {
  const mode = useGhostStore((s) => s.mode);
  const mesh = useGhostStore((s) => s.mesh);
  const setMesh = useGhostStore((s) => s.setMesh);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const runDemo = useCallback(async () => {
    setBusy(true);
    setErr(null);
    try {
      const r = await fetch(`${API_BASE}/v1/mesh/demo/story`, { method: 'POST' });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const body = (await r.json()) as Record<string, unknown>;
      setMesh({
        label: 'SIMULATED_MESH',
        bStatus: String(body.b_status ?? ''),
        cStatus: String(body.c_status ?? ''),
        eQuarantined: Boolean(body.e_quarantined),
        bFirstExperiment: String(body.b_experiments_first ?? ''),
      });
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Mesh demo failed');
    } finally {
      setBusy(false);
    }
  }, [setMesh]);

  if (mode !== 'evidence') return null;

  return (
    <section className="mesh-panel" aria-label="GhostMesh federated knowledge">
      <h2 className="a11y-heading">GhostMesh</h2>
      <p className="promotion-boundary-note">SIMULATED_MESH — raw evidence stays local</p>
      <button type="button" disabled={busy} onClick={() => void runDemo()}>
        {busy ? 'Running…' : 'RUN M13 DEMO STORY'}
      </button>
      {err && <p role="alert">{err}</p>}
      {mesh && (
        <>
          <MetricRow label="Environment" value={mesh.label} />
          <MetricRow label="Node B validation" value={mesh.bStatus} />
          <MetricRow label="Node C (negative transfer)" value={mesh.cStatus} />
          <MetricRow label="Poison quarantined (E)" value={mesh.eQuarantined ? 'yes' : 'no'} />
          <MetricRow label="B first experiment" value={mesh.bFirstExperiment} />
        </>
      )}
    </section>
  );
}
