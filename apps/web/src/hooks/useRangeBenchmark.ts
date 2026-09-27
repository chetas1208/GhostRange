import { useEffect, useState } from 'react';
import { useGhostStore } from '../state/store';

export type RunBenchmarkJson = {
  provisioning_ms?: number;
  boot_ms?: number;
  execution_ms?: number;
  verification_ms?: number;
  teardown_ms?: number;
  total_ms?: number;
  estimated_cost_usd?: number;
  live_provider?: string;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000';

/** Fetches orchestrator benchmark when live range id is known. */
export function useRangeBenchmark(): {
  benchmark: RunBenchmarkJson | null;
  loading: boolean;
  error: string | null;
} {
  const rangeId = useGhostStore((s) => s.streamRangeId ?? s.range?.id ?? null);
  const dataSource = useGhostStore((s) => s.dataSource);
  const phase = useGhostStore((s) => s.campaignPhase);
  const [benchmark, setBenchmark] = useState<RunBenchmarkJson | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (dataSource !== 'live' || !rangeId) {
      setBenchmark(null);
      setError(null);
      return;
    }
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/v1/ranges/${rangeId}/benchmark`);
        if (!res.ok) throw new Error(`${res.status}`);
        const json = (await res.json()) as RunBenchmarkJson;
        if (!cancelled) setBenchmark(json);
      } catch (e) {
        if (!cancelled) {
          setBenchmark(null);
          setError(e instanceof Error ? e.message : 'benchmark unavailable');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void load();
    const id = window.setInterval(load, 5000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [dataSource, rangeId, phase]);

  return { benchmark, loading, error };
}
