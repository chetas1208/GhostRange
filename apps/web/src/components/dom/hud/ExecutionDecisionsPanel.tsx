import { useMemo } from 'react';
import { useGhostStore } from '../../../state/store';

/** §10.7 / INTERACTION §3 — persistent DOM decision list (Execution mode). */
export function ExecutionDecisionsPanel() {
  const mode = useGhostStore((s) => s.mode);
  const decisionsRecord = useGhostStore((s) => s.decisions);
  const decisions = useMemo(() => Object.values(decisionsRecord), [decisionsRecord]);
  const setSelection = useGhostStore((s) => s.setSelection);

  if (mode !== 'execution' || decisions.length === 0) return null;

  return (
    <aside className="execution-decisions-panel" aria-label="Scheduler decisions">
      <div className="a11y-heading">Decisions</div>
      <ul className="a11y-entity-list">
        {decisions.map((d) => (
          <li key={d.id}>
            <button
              type="button"
              className="a11y-entity-item"
              onClick={() => setSelection({ kind: 'decision', id: d.id })}
            >
              {d.target_resource_class} · {d.reason_codes[0] ?? d.id.slice(-6)}
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
