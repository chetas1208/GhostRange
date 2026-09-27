import { MetricRow } from '../common/MetricRow';
import { StatusBadge } from '../common/StatusBadge';
import { useGhostStore } from '../../../state/store';

export function ComputeInspector({ workerId }: { workerId: string }) {
  const w = useGhostStore((s) => s.workers[workerId]);
  if (!w) return null;

  return (
    <>
      <header className="inspector-header">
        <h2>Compute</h2>
        <StatusBadge status={w.status} />
      </header>
      <MetricRow label="Resource ID" value={w.id.slice(0, 14)} />
      {w.provider_instance_id && <MetricRow label="Provider ID" value={w.provider_instance_id} />}
      <MetricRow label="Provider" value={w.provider ?? '—'} />
      <MetricRow label="Class" value={w.resource_class} />
      <MetricRow label="Region" value={w.region} />
      <MetricRow label="Rate (pinned)" value={`$${w.cost_per_hour_usd.toFixed(4)}/hr`} />
      <MetricRow label="Billing quantum" value="1 hr min (Vultr policy)" />
      <MetricRow label="CPU/RAM telemetry" value="NOT OBSERVABLE" />
    </>
  );
}
