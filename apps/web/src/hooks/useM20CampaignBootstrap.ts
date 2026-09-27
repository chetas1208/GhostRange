import { useEffect } from 'react';
import { API_BASE } from '../config/apiBase';
import { startM20CampaignAndStream } from '../events/campaignStream';

/** Production / live: auto-start real M20 campaign (no fixture reducer). */
export function useM20CampaignBootstrap() {
  // Only auto-start when explicitly enabled at build time (prod compose sets false).
  const enabled = import.meta.env.VITE_BOOTSTRAP_M20 === 'true';
  const dataSource = import.meta.env.VITE_DATA_SOURCE ?? 'fixture';

  useEffect(() => {
    if (!enabled || dataSource !== 'live') return;
    if (new URLSearchParams(window.location.search).get('rangeId')) return;
    startM20CampaignAndStream(API_BASE).catch(() => {
      /* CommandSurface / error banner */
    });
  }, [dataSource, enabled]);
}
