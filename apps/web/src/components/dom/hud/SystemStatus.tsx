import { selectConnectionStatus } from '../../../state/selectors';
import { useGhostStore } from '../../../state/store';
import { useTourStore } from '../../../tour/tourStore';
import { CostIndicator } from './CostIndicator';
import { WorkerCount } from './WorkerCount';

export function SystemStatus() {
  const connection = useGhostStore(selectConnectionStatus);
  const tourReplay = useTourStore(
    (s) => s.isTourSession && (s.status === 'RUNNING' || s.status === 'PAUSED' || s.showSummary),
  );
  const connLabel = tourReplay
    ? '◇ CONTROLLED REPLAY'
    : connection === 'LIVE'
      ? '● LIVE'
      : connection === 'REPLAY'
        ? '◷ HISTORY'
        : connection === 'FIXTURE'
          ? '◇ SIMULATED'
          : '○ OFFLINE';

  return (
    <header className="hud top-right system-status">
      <span className={`conn conn-${connection.toLowerCase()}`} title={connection}>
        {connLabel}
      </span>
      <CostIndicator />
      <WorkerCount />
    </header>
  );
}
