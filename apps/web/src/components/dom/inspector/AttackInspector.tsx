import { MetricRow } from '../common/MetricRow';
import { useGhostStore } from '../../../state/store';
import { selectActiveAttack, selectWorldAssets } from '../../../state/selectors';

export function AttackInspector({ worldId }: { worldId: string }) {
  const attack = useGhostStore((s) => selectActiveAttack(s, worldId));
  const assets = useGhostStore((s) => selectWorldAssets(s, worldId));
  const setSelection = useGhostStore((s) => s.setSelection);

  const hops = attack?.path_asset_ids ?? [];

  return (
    <>
      <header className="inspector-header">
        <h2>Attack path</h2>
      </header>
      <MetricRow label="Status" value={attack?.active ? 'ACTIVE' : 'HISTORICAL'} />
      <MetricRow label="Hops" value={String(hops.length)} />
      <nav aria-label="Attack hops">
        <ul className="a11y-entity-list">
          {hops.map((id, i) => {
            const asset = assets.find((a) => a.id === id);
            return (
              <li key={id}>
                <button
                  type="button"
                  className="a11y-entity-item"
                  onClick={() => setSelection({ kind: 'asset', id })}
                >
                  {i + 1}. {asset?.hostname ?? asset?.role ?? id.slice(-6)}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
    </>
  );
}
