import { normalizeEnvelope } from '../state/normalizeEnvelope';
import type { GhostEvent } from '../state/types';
import { useGhostStore } from '../state/store';

export type SseStatus = 'idle' | 'connecting' | 'open' | 'reconnecting' | 'closed' | 'failed';

type SnapshotResponse = {
  sequence: number;
  events?: Record<string, unknown>[];
};

let activeSource: EventSource | null = null;
let activeRangeId: string | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

function applyBatch(events: GhostEvent[]) {
  if (events.length) useGhostStore.getState().dispatchEvents(events);
}

export function disconnectCampaignStream() {
  if (reconnectTimer) clearTimeout(reconnectTimer);
  reconnectTimer = null;
  activeSource?.close();
  activeSource = null;
  activeRangeId = null;
  useGhostStore.setState({ streamConnected: false, sseStatus: 'closed' });
}

/** Snapshot first, then SSE after cursor (no overwrite of newer state). */
export async function connectCampaignStream(apiBase: string, rangeId: string): Promise<void> {
  if (activeRangeId === rangeId && activeSource?.readyState === EventSource.OPEN) return;

  disconnectCampaignStream();
  activeRangeId = rangeId;

  useGhostStore.setState({
    dataSource: 'live',
    streamConnected: false,
    sseStatus: 'connecting',
    streamError: null,
    streamRangeId: rangeId,
  });

  let sinceSeq = 0;
  try {
    const snapRes = await fetch(`${apiBase}/v1/ranges/${rangeId}/snapshot`);
    if (!snapRes.ok) throw new Error(`snapshot ${snapRes.status}`);
    const snap = (await snapRes.json()) as SnapshotResponse;
    sinceSeq = snap.sequence ?? 0;
    const batch: GhostEvent[] = (snap.events ?? []).map((e, i) =>
      normalizeEnvelope(e, (snap.sequence ?? 0) - (snap.events?.length ?? 0) + i + 1),
    );
    applyBatch(batch);
    useGhostStore.setState({ lastEventSeq: sinceSeq });
  } catch (err) {
    useGhostStore.setState({
      sseStatus: 'failed',
      streamError: err instanceof Error ? err.message : 'snapshot failed',
    });
    throw err;
  }

  const url = `${apiBase}/v1/ranges/${rangeId}/stream?after=${sinceSeq}`;
  const es = new EventSource(url);
  activeSource = es;

  es.onopen = () => {
    useGhostStore.setState({ streamConnected: true, sseStatus: 'open', live: true });
  };

  const ingest = (raw: Record<string, unknown>, seqHint?: number) => {
    const seq = Number(raw.sequence ?? seqHint ?? useGhostStore.getState().lastEventSeq + 1);
    const id = String(raw.event_id ?? raw.id ?? '');
    const st = useGhostStore.getState();
    if (seq <= st.lastEventSeq && id && st.processedEventIds.has(id)) return;
    if (id && st.processedEventIds.has(id)) return;
    applyBatch([normalizeEnvelope(raw, seq)]);
    useGhostStore.setState({ lastEventSeq: Math.max(st.lastEventSeq, seq) });
  };

  es.onmessage = (msg) => {
    try {
      const raw = JSON.parse(msg.data) as Record<string, unknown>;
      const seqFromId = msg.lastEventId ? Number(msg.lastEventId) : undefined;
      ingest(raw, seqFromId);
    } catch {
      /* ignore malformed */
    }
  };

  es.onerror = () => {
    useGhostStore.setState({
      streamConnected: false,
      sseStatus: 'reconnecting',
      streamError: 'SSE reconnecting…',
    });
    if (es.readyState === EventSource.CLOSED && activeRangeId === rangeId) {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        void connectCampaignStream(apiBase, rangeId);
      }, 1500);
    }
  };
}

export async function startM20CampaignAndStream(apiBase: string): Promise<{
  range_id: string;
  campaign_id?: string;
}> {
  const res = await fetch(`${apiBase}/v1/campaigns/golden`, { method: 'POST' });
  if (!res.ok) throw new Error(`campaign ${res.status}`);
  const body = (await res.json()) as {
    range_id: string;
    campaign?: { campaign_id?: string };
    report?: { incident_summary?: string };
  };

  useGhostStore.getState().reset();
  useGhostStore.setState({
    range: {
      id: body.range_id,
      slug: 'm20-golden',
      label: body.report?.incident_summary?.slice(0, 56) ?? 'M20 campaign',
    },
    campaignId: body.campaign?.campaign_id ?? null,
    dataSource: 'live',
  });

  await connectCampaignStream(apiBase, body.range_id);
  return { range_id: body.range_id, campaign_id: body.campaign?.campaign_id };
}
