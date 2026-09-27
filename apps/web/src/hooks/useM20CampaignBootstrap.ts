import { useEffect } from 'react';
import { API_BASE } from '../config/apiBase';
import { startM20CampaignAndStream } from '../events/campaignStream';

/** Production / live: auto-start real M20 campaign (no fixture reducer). */
export function useM20CampaignBootstrap() {
  const enabled =
    import.meta.env.VITE_BOOTSTRAP_M20 === 'true' ||
    (import.meta.env.PROD && import.meta.env.VITE_DATA_SOURCE === 'live');
  const dataSource = import.meta.env.VITE_DATA_SOURCE ?? 'fixture';

  useEffect(() => {
    if (!enabled || dataSource !== 'live') return;
    if (new URLSearchParams(window.location.search).get('rangeId')) return;
    startM20CampaignAndStream(API_BASE).catch(() => {
      /* CommandSurface / error banner */
    });
  }, [dataSource, enabled]);
}
