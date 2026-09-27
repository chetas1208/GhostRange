import { useGhostStore } from '../../state/store';
import { selectWorkerCount } from '../../state/selectors';

const MODE_LABEL = {
  multiverse: 'MULTIVERSE',
  execution: 'EXECUTION',
  evidence: 'EVIDENCE',
} as const;

export function HudChrome() {
  const range = useGhostStore((s) => s.range);
  const mode = useGhostStore((s) => s.mode);
  const dataSource = useGhostStore((s) => s.dataSource);
  const streamConnected = useGhostStore((s) => s.streamConnected);
  const provider = useGhostStore((s) => s.activeProvider);
  const cost = useGhostStore((s) => s.totalCostUsd);
  const workers = useGhostStore(selectWorkerCount);

  const sourceLabel = dataSource === 'live' ? (streamConnected ? 'LIVE' : 'LIVE (offline)') : 'FIXTURE';
  const sourceClass =
    dataSource === 'live' && streamConnected ? 'source live' : dataSource === 'fixture' ? 'source fixture' : 'source offline';

  return (
    <>
      <header className="hud top-left">
        <div className="brand">GHOSTRANGE</div>
        <div className="sub">range / {range?.slug ?? 'ghostrange-auth-lab-v1'}</div>
      </header>
      <header className="hud top-center">{MODE_LABEL[mode]}</header>
      <header className="hud top-right">
        <span className={sourceClass}>{sourceLabel}</span>
        {provider && <span className="provider">{provider === 'mock' ? 'MOCK' : provider.toUpperCase()}</span>}
        <span>${cost.toFixed(2)}</span>
        <span>{workers} WORKERS</span>
      </header>
    </>
  );
}
