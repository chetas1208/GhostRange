import { useGhostStore } from '../../state/store';
import { selectConnectionStatus, selectWorkerCount } from '../../state/selectors';
import { EnvironmentBadge } from './EnvironmentBadge';

function countTasks(state: ReturnType<typeof useGhostStore.getState>, status: string) {
  return Object.values(state.tasks).filter((t) => t.status === status).length;
}

export function MissionStatus() {
  const campaignId = useGhostStore((s) => s.campaignId ?? s.range?.id ?? null);
  const phase = useGhostStore((s) => s.campaignPhase);
  const connection = useGhostStore(selectConnectionStatus);
  const workerCount = useGhostStore(selectWorkerCount);
  const worlds = useGhostStore((s) => Object.values(s.worlds).filter((w) => !w.destroyed).length);
  const queued = useGhostStore((s) => countTasks(s, 'QUEUED'));
  const running = useGhostStore((s) => countTasks(s, 'RUNNING'));
  const failed = useGhostStore((s) => countTasks(s, 'FAILED'));

  const campaignState = phase ?? (connection === 'DISCONNECTED' ? 'STALE' : 'UNKNOWN');
  const setSelection = useGhostStore((s) => s.setSelection);

  return (
    <div className="tactical-mission-status hud" role="status" aria-live="polite">
      <span className="tactical-mission-id" title="Campaign / range">
        {campaignId ? campaignId.slice(0, 12) : 'NO CAMPAIGN'}
      </span>
      <EnvironmentBadge />
      <span className="tactical-campaign-state" title="Campaign state">
        {campaignState}
      </span>
      <span className="tactical-stat" title="Active worlds">
        W {worlds}
      </span>
      <span className="tactical-stat" title="Ready/busy workers">
        S {workerCount}
      </span>
      <span className="tactical-stat" title="Queued tasks">
        Q {queued}
      </span>
      <span className="tactical-stat" title="Running tasks">
        R {running}
      </span>
      {failed > 0 && (
        <span className="tactical-stat tactical-stat-fail" title="Failed tasks">
          F {failed}
        </span>
      )}
      <button
        type="button"
        className="ticker-line"
        style={{ marginLeft: 8 }}
        onClick={() => setSelection({ kind: 'cost' })}
      >
        COST
      </button>
    </div>
  );
}
