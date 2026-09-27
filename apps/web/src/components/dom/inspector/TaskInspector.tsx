import { MetricRow } from '../common/MetricRow';
import { StatusBadge } from '../common/StatusBadge';
import { useMemo } from 'react';
import { useGhostStore } from '../../../state/store';
import { useRangeTiming } from '../../../hooks/useRangeTiming';
import { useCampaignCost } from '../../../hooks/useCampaignCost';

export function TaskInspector({ taskId }: { taskId: string }) {
  const t = useGhostStore((s) => s.tasks[taskId]);
  const timing = useGhostStore((s) => s.taskTiming[taskId]);
  const decisionsRecord = useGhostStore((s) => s.decisions);
  const d = useMemo(
    () => Object.values(decisionsRecord).find((x) => x.task_id === taskId),
    [decisionsRecord, taskId],
  );
  const rangeTiming = useRangeTiming('M2_RUN_TOTAL');
  const { cost } = useCampaignCost();

  if (!t) return null;

  return (
    <>
      <header className="inspector-header">
        <h2>{t.label ?? t.id}</h2>
        <StatusBadge status={t.status} />
      </header>
      <MetricRow label="Type" value={t.task_type} />
      <MetricRow label="Priority" value={String(t.priority ?? '—')} />
      <MetricRow label="World" value={t.world_id.slice(0, 12)} />
      {timing?.queued_at && <MetricRow label="Queued" value={timing.queued_at.slice(11, 19)} />}
      {timing?.started_at && <MetricRow label="Started" value={timing.started_at.slice(11, 19)} />}
      {timing?.completed_at && <MetricRow label="Completed" value={timing.completed_at.slice(11, 19)} />}
      {timing?.queued_at && timing?.started_at && (
        <MetricRow
          label="Queue wait"
          value={`${Math.max(0, Date.parse(timing.started_at) - Date.parse(timing.queued_at))} ms`}
        />
      )}
      {d && (
        <section className="scheduler-block">
          <h3>Scheduler</h3>
          <MetricRow label="Resource" value={d.target_resource_class} />
          <MetricRow label="Why" value={d.reason_codes.join(', ')} />
          <MetricRow label="PROJECTED (sched)" value={`$${d.estimated_cost_usd.toFixed(4)}`} />
        </section>
      )}
      {rangeTiming?.historical && (
        <section className="timing-block">
          <h3>Historical timing</h3>
          <MetricRow label="Samples" value={String(rangeTiming.historical.sample_count)} />
          {rangeTiming.historical.p50_ms != null && (
            <MetricRow label="P50" value={`${(rangeTiming.historical.p50_ms / 1000).toFixed(1)} s`} />
          )}
          {rangeTiming.historical.p95_ms != null && (
            <MetricRow label="P95" value={`${(rangeTiming.historical.p95_ms / 1000).toFixed(1)} s`} />
          )}
          {rangeTiming.historical.estimate_confidence === 'LOW_SAMPLE_COUNT' && (
            <MetricRow label="Estimate" value="LOW SAMPLE COUNT" />
          )}
          {rangeTiming.active_estimate?.estimated_remaining_ms != null && (
            <MetricRow
              label="Est. remaining"
              value={`${(rangeTiming.active_estimate.estimated_remaining_ms / 1000).toFixed(1)} s`}
            />
          )}
          {rangeTiming.active_estimate?.estimate_basis && (
            <MetricRow label="Estimate basis" value={rangeTiming.active_estimate.estimate_basis} />
          )}
        </section>
      )}
      {cost?.display?.known_total && (
        <section className="cost-block">
          <h3>Cost (canonical API)</h3>
          <MetricRow label="Known total" value={cost.display.known_total} />
          <MetricRow label="Semantic" value={cost.display.semantic_type ?? '—'} />
        </section>
      )}
    </>
  );
}
