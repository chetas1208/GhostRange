import { useEffect } from 'react';
import { API_BASE } from '../config/apiBase';
import { connectCampaignStream } from '../events/campaignStream';
import { useGhostStore } from '../state/store';

function resolveRangeId(): string {
  const fromUrl = new URLSearchParams(window.location.search).get('rangeId');
  return (import.meta.env.VITE_RANGE_ID as string | undefined) ?? fromUrl ?? '';
}

/** Live mode: snapshot + native EventSource (after=seq). */
export function useLiveBootstrap(enabled = false) {
  const streamRangeId = useGhostStore((s) => s.streamRangeId);
  useEffect(() => {
    if (!enabled) return;

    const RANGE_ID = resolveRangeId() || streamRangeId || '';
    if (!RANGE_ID) {
      // No campaign yet is the normal empty state, not an error: the
      // EmptyChamberHint ("Press ⌘/Ctrl+K to create a range") guides the user.
      useGhostStore.setState({
        dataSource: 'live',
        streamConnected: false,
        live: false,
        streamError: null,
        sseStatus: 'idle',
      });
      return;
    }

    let cancelled = false;
    connectCampaignStream(API_BASE, RANGE_ID).catch((err) => {
      if (cancelled) return;
      useGhostStore.setState({
        streamConnected: false,
        live: false,
        streamError: err instanceof Error ? err.message : 'Live bootstrap failed',
        sseStatus: 'failed',
      });
    });

    return () => {
      cancelled = true;
    };
  }, [enabled, streamRangeId]);
}
