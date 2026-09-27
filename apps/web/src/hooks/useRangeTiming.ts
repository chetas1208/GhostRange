import { useEffect, useState } from 'react';
import { API_BASE } from '../config/apiBase';
import { useGhostStore } from '../state/store';

export type RangeTimingResponse = {
  benchmark_decomposition?: Record<string, number>;
  historical?: {
    sample_count: number;
    p50_ms?: number | null;
    p95_ms?: number | null;
    estimate_confidence?: string;
  };
  active_estimate?: {
    elapsed_ms?: number | null;
    estimated_remaining_ms?: number | null;
    estimate_basis?: string;
    sample_count?: number;
  };
};

export function useRangeTiming(operationType = 'M2_RUN_TOTAL') {
  const rangeId = useGhostStore((s) => s.streamRangeId ?? s.range?.id ?? null);
  const dataSource = useGhostStore((s) => s.dataSource);
  const [timing, setTiming] = useState<RangeTimingResponse | null>(null);

  useEffect(() => {
    if (dataSource !== 'live' || !rangeId) {
      setTiming(null);
      return;
    }
    let cancelled = false;
    const load = async () => {
      try {
        const q = new URLSearchParams({ operation_type: operationType });
        const res = await fetch(`${API_BASE}/v1/ranges/${rangeId}/timing?${q}`);
        if (!res.ok) return;
        const json = (await res.json()) as RangeTimingResponse;
        if (!cancelled) setTiming(json);
      } catch {
        if (!cancelled) setTiming(null);
      }
    };
    void load();
    const id = window.setInterval(load, 5000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [dataSource, rangeId, operationType]);

  return timing;
}
