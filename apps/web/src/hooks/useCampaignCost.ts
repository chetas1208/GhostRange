import { useEffect, useState } from 'react';
import { useGhostStore } from '../state/store';

export type CampaignCostResponse = {
  semantic_type?: string;
  confidence?: string;
  total_known_usd_micros?: number;
  unknown_components?: string[];
  finalized?: boolean;
  categories?: Record<string, number>;
  display?: {
    semantic_type?: string;
    known_total?: string;
    finalized?: boolean;
    unknown_components?: string[];
  };
};

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000';

/** Backend canonical cost — frontend does not compute billing formulas. */
export function useCampaignCost(): {
  cost: CampaignCostResponse | null;
  loading: boolean;
  error: string | null;
} {
  const rangeId = useGhostStore((s) => s.streamRangeId ?? s.range?.id ?? null);
  const dataSource = useGhostStore((s) => s.dataSource);
  const costRevision = useGhostStore((s) => s.costRevision);
  const [cost, setCost] = useState<CampaignCostResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (dataSource !== 'live' || !rangeId) {
      setCost(null);
      return;
    }
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE}/v1/ranges/${rangeId}/cost`);
        if (!res.ok) throw new Error(String(res.status));
        const json = (await res.json()) as CampaignCostResponse;
        if (!cancelled) {
          setCost(json);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          setCost(null);
          setError(e instanceof Error ? e.message : 'cost unavailable');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void load();
    const id = window.setInterval(load, 8000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [dataSource, rangeId, costRevision]);

  return { cost, loading, error };
}
