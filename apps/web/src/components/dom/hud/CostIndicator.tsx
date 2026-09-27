import { useGhostStore } from '../../../state/store';
import { useCampaignCost } from '../../../hooks/useCampaignCost';
import { selectConnectionStatus } from '../../../state/selectors';

function fixtureCostLabel(usd: number): string {
  return `SIM EST. $${usd.toFixed(4)}`;
}

export function CostIndicator() {
  const fixtureUsd = useGhostStore((s) => s.totalCostUsd);
  const connection = useGhostStore(selectConnectionStatus);
  const semantic = useGhostStore((s) => s.costSemanticType);
  const { cost, error } = useCampaignCost();

  if (connection === 'LIVE' || connection === 'DISCONNECTED') {
    const label = semantic ?? cost?.display?.semantic_type ?? 'ACCRUED_ESTIMATE';
    const known = cost?.display?.known_total;
    const unknown = cost?.unknown_components?.length ?? cost?.display?.unknown_components?.length ?? 0;
    if (known) {
      return (
        <span className="cost-indicator" data-testid="cost-indicator" title={error ?? 'Canonical backend cost'}>
          {label.replace(/_/g, ' ')} {known}
          {unknown > 0 ? ' · PARTIAL' : ''}
        </span>
      );
    }
    if (error) {
      return (
        <span className="cost-indicator" data-testid="cost-indicator" title={error}>
          COST UNKNOWN
        </span>
      );
    }
    return (
      <span className="cost-indicator" data-testid="cost-indicator" title="Waiting for backend cost snapshot">
        ACCRUED EST. —
      </span>
    );
  }

  return (
    <span className="cost-indicator" data-testid="cost-indicator" title="Fixture replay — not provider-billed">
      {fixtureCostLabel(fixtureUsd)}
    </span>
  );
}
