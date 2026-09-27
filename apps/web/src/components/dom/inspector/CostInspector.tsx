import { useCampaignCost } from '../../../hooks/useCampaignCost';
import { MetricRow } from '../common/MetricRow';

export function CostInspector() {
  const { cost, error } = useCampaignCost();
  if (error) {
    return (
      <>
        <header className="inspector-header">
          <h2>Campaign cost</h2>
        </header>
        <MetricRow label="Status" value="UNKNOWN" />
        <p className="muted">{error}</p>
      </>
    );
  }
  if (!cost) {
    return (
      <>
        <header className="inspector-header">
          <h2>Campaign cost</h2>
        </header>
        <MetricRow label="Status" value="NOT AVAILABLE" />
      </>
    );
  }
  const cats = cost.categories ?? {};
  const unknown = cost.unknown_components ?? [];
  return (
    <>
      <header className="inspector-header">
        <h2>Campaign cost</h2>
      </header>
      <MetricRow label="Basis" value={cost.semantic_type?.replace(/_/g, ' ') ?? 'ACCRUED ESTIMATE'} />
      <MetricRow label="Known total" value={cost.display?.known_total ?? '—'} />
      {cats.COMPUTE_EPHEMERAL != null && (
        <MetricRow label="Ephemeral compute" value={`${(cats.COMPUTE_EPHEMERAL / 1_000_000).toFixed(6)} USD (micros basis)`} />
      )}
      {cats.INFERENCE != null && (
        <MetricRow label="Inference" value={`${(cats.INFERENCE / 1_000_000).toFixed(6)} USD (micros basis)`} />
      )}
      {unknown.length > 0 && (
        <MetricRow label="Unresolved" value={unknown.join(', ')} />
      )}
      <MetricRow label="Finalized" value={cost.finalized ? 'YES' : 'NO'} />
    </>
  );
}
