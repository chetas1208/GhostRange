import { useEffect, useState } from 'react';
import { useGhostStore } from '../state/store';
import { selectConnectionStatus } from '../state/selectors';

function parseMs(iso: string | undefined): number | null {
  if (!iso) return null;
  const t = Date.parse(iso);
  return Number.isFinite(t) ? t : null;
}

/** Wall-clock elapsed since first logged event (live) or frozen during history scrub. */
export function useCampaignElapsedMs(): number | null {
  const eventLog = useGhostStore((s) => s.eventLog);
  const liveBuf = useGhostStore((s) => s.liveEventBuffer);
  const replayScrubbing = useGhostStore((s) => s.replayScrubbing);
  const replayTimeMs = useGhostStore((s) => s.replayTimeMs);
  const connection = useGhostStore(selectConnectionStatus);

  const startMs =
    parseMs(liveBuf[0]?.occurred_at) ??
    parseMs(eventLog[0]?.occurred_at) ??
    null;

  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (replayScrubbing || connection === 'REPLAY' || connection === 'FIXTURE') return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [replayScrubbing, connection]);

  if (startMs == null) return null;
  if (replayScrubbing || connection === 'REPLAY') return Math.max(0, replayTimeMs);
  return Math.max(0, now - startMs);
}

export function formatDurationMs(ms: number | null): string {
  if (ms == null) return '—';
  const sec = Math.floor(ms / 1000);
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  if (h > 0) return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}
