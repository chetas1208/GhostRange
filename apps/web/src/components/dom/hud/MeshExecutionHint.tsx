import { useGhostStore } from '../../../state/store';

/** Agent 34 — Execution tab: remote prior ≠ Scheduler-owned work. */
export function MeshExecutionHint() {
  const mode = useGhostStore((s) => s.mode);
  const mesh = useGhostStore((s) => s.mesh);
  if (mode !== 'execution' || !mesh?.bFirstExperiment) return null;
  return (
    <p className="mesh-execution-hint" aria-live="polite">
      REMOTE PRIOR → GHOSTDIRECTOR → LOCAL EXPERIMENT → GHOSTSCHEDULER (first: {mesh.bFirstExperiment})
    </p>
  );
}
