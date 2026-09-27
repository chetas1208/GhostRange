import { MetricRow } from '../common/MetricRow';
import { CodeBlock } from '../common/CodeBlock';
import { LogViewer } from '../common/LogViewer';
import { useMemo } from 'react';
import { useGhostStore } from '../../../state/store';
import type { Selection } from '../../../state/types';

export function EvidenceInspector({ selection }: { selection: Selection }) {
  const claim = useGhostStore((s) =>
    selection.kind === 'claim' ? s.claims[selection.id] : undefined,
  );
  const artifact = useGhostStore((s) =>
    selection.kind === 'artifact' ? s.artifacts[selection.id] : undefined,
  );
  const artifactsRecord = useGhostStore((s) => s.artifacts);
  const artifacts = useMemo(() => Object.values(artifactsRecord), [artifactsRecord]);
  const setSelection = useGhostStore((s) => s.setSelection);

  if (selection.kind === 'claim' && claim) {
    return (
      <>
        <header className="inspector-header">
          <h2>Claim</h2>
        </header>
        <p className="claim-text">{claim.statement}</p>
        <MetricRow label="Anchored" value={claim.anchored ? 'Yes' : 'No'} />
        <MetricRow label="Verified" value={claim.verified ? 'Yes' : 'Pending'} />
        <nav aria-label="Evidence artifacts">
          <h3 className="a11y-heading">Artifacts</h3>
          <ul className="a11y-entity-list">
            {artifacts.map((a) => (
              <li key={a.id}>
                <button
                  type="button"
                  className="a11y-entity-item"
                  onClick={() => setSelection({ kind: 'artifact', id: a.id })}
                >
                  {a.artifact_type} · {a.id.slice(-6)}
                </button>
              </li>
            ))}
          </ul>
        </nav>
      </>
    );
  }

  if (selection.kind === 'artifact' && artifact) {
    const lines = artifact.output ? artifact.output.split('\n') : [];
    return (
      <>
        <header className="inspector-header">
          <h2>Artifact #{artifact.id.slice(-4).toUpperCase()}</h2>
        </header>
        <MetricRow label="Type" value={artifact.artifact_type} />
        <MetricRow label="World" value={artifact.world_id.slice(0, 10)} />
        <MetricRow label="SHA-256" value={`${artifact.content_hash.slice(0, 16)}…`} />
        {artifact.command && <CodeBlock title="Command" code={artifact.command} />}
        {lines.length > 0 && (
          <>
            <h3 className="a11y-heading">Output</h3>
            <LogViewer lines={lines} />
          </>
        )}
      </>
    );
  }

  return null;
}
