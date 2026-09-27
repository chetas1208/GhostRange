import { useIntelligenceHealth } from '../../../hooks/useIntelligenceHealth';

const STATUS_GLYPH: Record<string, string> = {
  READY: '●',
  DEGRADED: '◐',
  OFFLINE: '○',
};

/**
 * Small HUD status element for the optional model-assisted-inference provider (existing
 * Vultr Serverless Inference by default, or the local CPU-only Laya provider when the
 * backend has INTELLIGENCE_PROVIDER=laya-local set — see health_routes.py's
 * `checks.intelligence` block). Renders nothing when no provider is configured at all, so
 * it is a no-op in the common case and never claims a primary UI slot.
 */
export function IntelligenceBadge() {
  const health = useIntelligenceHealth();
  if (!health || health.status === 'NOT_CONFIGURED') return null;

  const glyph = STATUS_GLYPH[health.status] ?? '◇';
  const device = health.device ? String(health.device).toUpperCase() : 'REMOTE';
  const latency = typeof health.latency_ms === 'number' ? `${health.latency_ms}ms` : '—';
  const title = [
    `provider=${health.provider}`,
    `model=${health.model ?? 'unknown'}`,
    `mode=${health.mode ?? 'unknown'}`,
    health.detail ? `detail=${health.detail}` : null,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <span
      className={`intelligence-badge intelligence-${health.status.toLowerCase()}`}
      title={title}
      data-testid="intelligence-badge"
    >
      {glyph} INTEL:{device} {health.status} {latency}
    </span>
  );
}
