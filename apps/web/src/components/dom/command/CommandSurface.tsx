import { useEffect, useMemo, useState } from 'react';
import { API_BASE } from '../../../config/apiBase';
import { startM20CampaignAndStream } from '../../../events/campaignStream';
import { useGhostStore } from '../../../state/store';
import { OperatorIntegrations } from './OperatorIntegrations';
import { useTourStore } from '../../../tour/tourStore';

/** §14 Command surface — structured range preview, not a chat UI. */
export function CommandSurface() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const range = useGhostStore((s) => s.range);
  const worldsRecord = useGhostStore((s) => s.worlds);
  const taskCount = useGhostStore((s) => Object.keys(s.tasks).length);
  const streamError = useGhostStore((s) => s.streamError);
  const blocked = Boolean(streamError?.includes('auth'));
  const startTour = useTourStore((s) => s.startTour);
  const restartTour = useTourStore((s) => s.restartTour);
  const toursEnabled = import.meta.env.VITE_ENABLE_TOUR !== 'false';

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        if (!blocked) setOpen((v) => !v);
      }
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [blocked]);

  const preview = useMemo(() => {
    if (!range) return 'Start M20 golden campaign · auth-lab compose input';
    let worldCount = 0;
    let ready = 0;
    for (const id in worldsRecord) {
      const w = worldsRecord[id];
      if (w.parent_world_id) continue;
      worldCount++;
      if (w.network_ready) ready++;
    }
    return `${range.label} · ${worldCount} world(s) · ${ready} ready · ${taskCount} task(s)`;
  }, [range, worldsRecord, taskCount]);

  const startM20 = async () => {
    await startM20CampaignAndStream(API_BASE);
    setOpen(false);
  };

  if (!open) return null;

  return (
    <div className="command-palette command-surface" role="dialog" aria-label="Command surface">
      <div className="command-surface-preview">{preview}</div>
      <input
        autoFocus
        placeholder="Create range, inspect world, request verification…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') setOpen(false);
        }}
      />
      <div className="command-surface-hints">
        <span>Enter — dismiss</span>
        <span>Esc — close</span>
      </div>
      <div className="command-surface-actions">
        <button
          type="button"
          data-testid="start-m20-campaign"
          onClick={() => void startM20().catch(() => setOpen(false))}
        >
          Start M20 golden campaign
        </button>
        <button type="button" onClick={() => setOpen(false)}>
          Dismiss
        </button>
        {toursEnabled ? (
          <>
            <button
              type="button"
              data-testid="cmd-tour-guided"
              onClick={() => {
                startTour('guided');
                setOpen(false);
              }}
            >
              Take GhostRange tour
            </button>
            <button
              type="button"
              data-testid="cmd-tour-judge"
              onClick={() => {
                startTour('judge');
                setOpen(false);
              }}
            >
              Judge tour (~3 min)
            </button>
            <button
              type="button"
              onClick={() => {
                restartTour();
                setOpen(false);
              }}
            >
              Restart tour
            </button>
          </>
        ) : null}
      </div>
      <OperatorIntegrations />
    </div>
  );
}
