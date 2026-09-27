import { useGhostStore } from '../../state/store';
import { selectConnectionStatus } from '../../state/selectors';
import { useTourStore } from '../../tour/tourStore';

export function EnvironmentBadge() {
  const provider = useGhostStore((s) => s.activeProvider);
  const connection = useGhostStore(selectConnectionStatus);
  const tourReplay = useTourStore(
    (s) => s.isTourSession && (s.status === 'RUNNING' || s.status === 'PAUSED'),
  );

  let env: string;
  if (tourReplay) env = 'CONTROLLED REPLAY';
  else if (connection === 'FIXTURE') env = 'SIMULATED';
  else if (connection === 'LIVE' && provider === 'vultr') env = 'VULTR_LIVE';
  else if (connection === 'LIVE') env = provider === 'mock' ? 'LOCAL MOCK' : 'HYBRID';
  else if (connection === 'REPLAY') env = 'HISTORICAL REPLAY';
  else env = 'OFFLINE';

  return (
    <span className="tactical-env-badge" title="Execution environment">
      {env}
    </span>
  );
}
