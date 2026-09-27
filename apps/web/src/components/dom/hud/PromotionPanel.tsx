import { useCallback, useState } from 'react';
import { useGhostStore } from '../../../state/store';
import { MetricRow } from '../common/MetricRow';

import { API_BASE } from '../../../config/apiBase';

/** M11 — PREPARE PROMOTION (does not deploy). */
export function PromotionPanel() {
  const mode = useGhostStore((s) => s.mode);
  const promotion = useGhostStore((s) => s.promotion);
  const setPromotion = useGhostStore((s) => s.setPromotion);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const prepare = useCallback(async () => {
    setBusy(true);
    setErr(null);
    try {
      const r = await fetch(`${API_BASE}/v1/golden-path/runs?with_promotion=true`, { method: 'POST' });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const body = (await r.json()) as {
        promotion?: {
          candidate_id: string;
          state: string;
          change_candidate_hash: string;
          readiness_blockers?: string[];
        };
        bundle_digest?: string;
      };
      const p = body.promotion;
      if (!p) throw new Error('No promotion in response');
      setPromotion({
        candidateId: p.candidate_id,
        state: p.state,
        hash: p.change_candidate_hash,
        blockers: p.readiness_blockers ?? [],
        evidenceRoot: body.bundle_digest ?? '',
        patchPreview: '',
      });
      const detail = await fetch(`${API_BASE}/v1/promotion/candidates/${p.candidate_id}`);
      if (detail.ok) {
        const cand = (await detail.json()) as { patch_text?: string };
        setPromotion({
          candidateId: p.candidate_id,
          state: p.state,
          hash: p.change_candidate_hash,
          blockers: p.readiness_blockers ?? [],
          evidenceRoot: body.bundle_digest ?? '',
          patchPreview: cand.patch_text?.slice(0, 1200) ?? '',
        });
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Prepare failed');
    } finally {
      setBusy(false);
    }
  }, [setPromotion]);

  if (mode !== 'evidence') return null;

  return (
    <section className="promotion-panel" aria-label="GhostGate promotion">
      <h2 className="a11y-heading">Promotion (GhostGate)</h2>
      <p className="promotion-boundary-note">APPROVED ≠ DEPLOYED — human review only</p>
      <button type="button" disabled={busy} onClick={() => void prepare()}>
        {busy ? 'Preparing…' : 'PREPARE PROMOTION'}
      </button>
      {err && <p role="alert">{err}</p>}
      {promotion && (
        <>
          <MetricRow label="State" value={promotion.state} />
          <MetricRow label="Candidate" value={promotion.candidateId.slice(0, 8)} />
          <MetricRow label="Hash" value={`${promotion.hash.slice(0, 12)}…`} />
          {promotion.blockers.length > 0 && (
            <MetricRow label="Blockers" value={promotion.blockers.join(', ')} />
          )}
          {promotion.patchPreview && (
            <MetricRow label="Patch" value="Available in evidence export (not shown in spatial UI)" />
          )}
        </>
      )}
    </section>
  );
}
