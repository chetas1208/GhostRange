import { useMemo, useState } from 'react';
import { useShallow } from 'zustand/react/shallow';
import { MetricRow } from '../common/MetricRow';
import { StatusBadge } from '../common/StatusBadge';
import { useGhostStore } from '../../../state/store';
import { selectActiveAttack, selectWorldAssets } from '../../../state/selectors';

type Tab = 'overview' | 'compute' | 'evidence';

export function WorldInspector({ worldId }: { worldId: string }) {
  const [tab, setTab] = useState<Tab>('overview');
  const w = useGhostStore((s) => s.worlds[worldId]);
  const worldsRecord = useGhostStore((s) => s.worlds);
  const worlds = useMemo(
    () => Object.values(worldsRecord).filter((x) => !x.parent_world_id),
    [worldsRecord],
  );
  const workersRecord = useGhostStore((s) => s.workers);
  const workers = useMemo(
    () => Object.values(workersRecord).filter((x) => x.world_id === worldId),
    [workersRecord, worldId],
  );
  const artifactsRecord = useGhostStore((s) => s.artifacts);
  const artifacts = useMemo(
    () => Object.values(artifactsRecord).filter((x) => x.world_id === worldId),
    [artifactsRecord, worldId],
  );
  const attack = useGhostStore((s) => selectActiveAttack(s, worldId));
  const assets = useGhostStore(useShallow((s) => selectWorldAssets(s, worldId)));
  const runningTask = useGhostStore((s) =>
    Object.values(s.tasks).find((t) => t.world_id === worldId && t.status === 'RUNNING'),
  );
  const setSelection = useGhostStore((s) => s.setSelection);
  const focusWorld = useGhostStore((s) => s.focusWorld);
  const setMode = useGhostStore((s) => s.setMode);

  if (!w) return null;

  return (
    <>
      <header className="inspector-header">
        <h2>{w.label}</h2>
        <StatusBadge status={w.status} tone={w.status === 'FAILED' ? 'error' : 'active'} />
      </header>
      <nav className="inspector-tabs" aria-label="World inspector sections">
        {(['overview', 'compute', 'evidence'] as Tab[]).map((t) => (
          <button
            key={t}
            type="button"
            className={tab === t ? 'active' : ''}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </nav>
      {tab === 'overview' && (
        <section>
          <MetricRow label="World ID" value={w.id.slice(0, 12)} />
          <MetricRow label="Status" value={w.status} />
          {runningTask && <MetricRow label="Current task" value={runningTask.label ?? runningTask.id} />}
          <MetricRow label="Evidence" value={String(artifacts.length)} />
          {attack && (
            <button
              type="button"
              className="inspector-action"
              onClick={() => setSelection({ kind: 'attack', id: worldId, worldId })}
            >
              Inspect attack path ({attack.path_asset_ids.length} hops)
            </button>
          )}
          <nav aria-label="Worlds in range" className="a11y-section">
            <h3 className="a11y-heading">Worlds</h3>
            <ul className="a11y-entity-list">
              {worlds.map((rw) => (
                <li key={rw.id}>
                  <button
                    type="button"
                    className="a11y-entity-item"
                    onClick={() => {
                      setSelection({ kind: 'world', id: rw.id });
                      focusWorld(rw.id);
                    }}
                  >
                    {rw.label} — {rw.status}
                  </button>
                </li>
              ))}
            </ul>
          </nav>
          {attack && (
            <nav aria-label="Attack hops">
              <h3 className="a11y-heading">Attack hops</h3>
              <ul className="a11y-entity-list">
                {attack.path_asset_ids.map((id, i) => {
                  const asset = assets.find((a) => a.id === id);
                  return (
                    <li key={id}>
                      <button
                        type="button"
                        className="a11y-entity-item"
                        onClick={() => setSelection({ kind: 'attack', id: worldId, worldId })}
                      >
                        {i + 1}. {asset?.hostname ?? id.slice(-6)}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </nav>
          )}
        </section>
      )}
      {tab === 'compute' && (
        <section>
          {workers.length === 0 && <p className="muted">No compute resources.</p>}
          {workers.map((wr) => (
            <MetricRow key={wr.id} label={wr.resource_class} value={wr.status} />
          ))}
        </section>
      )}
      {tab === 'evidence' && (
        <section>
          {artifacts.length === 0 && <p className="muted">No artifacts yet.</p>}
          {artifacts.map((a) => (
            <button
              key={a.id}
              type="button"
              className="a11y-entity-item block"
              onClick={() => {
                setMode('evidence');
                setSelection({ kind: 'artifact', id: a.id });
              }}
            >
              {a.artifact_type} · {a.id.slice(-6)}
            </button>
          ))}
        </section>
      )}
    </>
  );
}
