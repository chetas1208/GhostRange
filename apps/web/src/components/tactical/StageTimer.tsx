import { formatDurationMs, useCampaignElapsedMs } from '../../hooks/useOperationTimer';
import { useRangeBenchmark } from '../../hooks/useRangeBenchmark';

export function StageTimer() {
  const elapsed = useCampaignElapsedMs();
  const { benchmark, error } = useRangeBenchmark();

  const expectedTotal =
    benchmark?.total_ms != null && benchmark.total_ms > 0 ? benchmark.total_ms : null;

  return (
    <div className="tactical-stage-timer hud" aria-label="Campaign timing">
      <span title="Elapsed since first event">
        ELAPSED {formatDurationMs(elapsed)}
      </span>
      <span title="Expected total from run benchmark when available">
        {expectedTotal != null
          ? `EXPECTED ${formatDurationMs(expectedTotal)} (RUN BENCHMARK)`
          : error
            ? 'ESTIMATE UNAVAILABLE'
            : 'ESTIMATE UNAVAILABLE'}
      </span>
    </div>
  );
}
