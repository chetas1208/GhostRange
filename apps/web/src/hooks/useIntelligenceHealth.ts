import { useEffect, useState } from 'react';

export type IntelligenceHealth = {
  provider: string;
  status: 'READY' | 'DEGRADED' | 'OFFLINE' | 'NOT_CONFIGURED' | string;
  device: string | null;
  model: string | null;
  latency_ms: number | null;
  mode: string | null;
  detail?: string;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000';

/**
 * Polls the existing `/health/ready` readiness surface for the `checks.intelligence` block
 * (see health_routes.py) — provider-agnostic status for whichever inference provider is
 * active: the pre-existing Vultr Serverless Inference path by default, or the optional
 * local, CPU-only Laya provider when the backend has INTELLIGENCE_PROVIDER=laya-local set.
 * Never mutates anything; a failed/slow poll just means the badge goes stale, it never
 * blocks or degrades any other part of the UI.
 */
export function useIntelligenceHealth(pollMs = 20000): IntelligenceHealth | null {
  const [health, setHealth] = useState<IntelligenceHealth | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const res = await fetch(`${API_BASE}/health/ready`);
        // /health/ready returns 503 when overall `ok` is false, but the `intelligence`
        // block is still present and meaningful in that body — read it regardless of
        // status code.
        const json = (await res.json()) as { checks?: { intelligence?: IntelligenceHealth } };
        const intel = json.checks?.intelligence;
        if (!cancelled && intel) setHealth(intel);
      } catch {
        // Backend unreachable: leave the last-known value in place rather than flapping
        // the badge on a single missed poll.
      }
    };
    void load();
    const id = window.setInterval(load, pollMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [pollMs]);

  return health;
}
