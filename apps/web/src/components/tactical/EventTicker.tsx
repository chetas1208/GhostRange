import { useGhostStore } from '../../state/store';

const MAX = 8;

export function EventTicker() {
  const entries = useGhostStore((s) => s.eventLog.slice(-MAX));

  if (entries.length === 0) return null;

  const focusFromLabel = (label: string) => {
    const worlds = useGhostStore.getState().worlds;
    for (const id in worlds) {
      if (label.toLowerCase().includes(id.slice(0, 6).toLowerCase())) {
        useGhostStore.getState().setSelection({ kind: 'world', id });
        useGhostStore.getState().focusWorld(id);
        return;
      }
    }
  };

  return (
    <div className="tactical-event-ticker hud bottom-ticker" aria-label="Recent events">
      {entries.map((e, i) => (
        <button
          key={`${e.occurred_at}-${i}`}
          type="button"
          className="ticker-line"
          onClick={() => focusFromLabel(e.label)}
        >
          <time dateTime={e.occurred_at}>{e.occurred_at.slice(11, 19)}</time> {e.label}
        </button>
      ))}
    </div>
  );
}
