import { useEffect } from 'react';
import { API_BASE } from '../config/apiBase';
import { connectCampaignStream } from '../events/campaignStream';
import { useGhostStore } from '../state/store';

const RANGE_ID = import.meta.env.VITE_RANGE_ID ?? '';

/** Live mode: snapshot + native EventSource (after=seq). */
export function useLiveBootstrap(enabled = false) {
  useEffect(() => {
    if (!enabled) return;

    if (!RANGE_ID) {
      useGhostStore.setState({
        dataSource: 'live',
        streamConnected: false,
        live: false,
        streamError: 'Live mode requires VITE_RANGE_ID or ⌘K Start M20 campaign',
        sseStatus: 'failed',
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
  }, [enabled]);
}
