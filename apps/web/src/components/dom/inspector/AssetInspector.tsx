import { MetricRow } from '../common/MetricRow';
import { useGhostStore } from '../../../state/store';

export function AssetInspector({ assetId }: { assetId: string }) {
  const a = useGhostStore((s) => s.assets[assetId]);
  if (!a) return null;

  return (
    <>
      <header className="inspector-header">
        <h2>{a.hostname}</h2>
      </header>
      <MetricRow label="OS" value={a.os_family} />
      <MetricRow label="Role" value={a.role} />
      {a.fractured && <MetricRow label="State" value="Compromised" />}
    </>
  );
}
