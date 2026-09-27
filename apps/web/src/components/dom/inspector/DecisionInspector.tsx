import { MetricRow } from '../common/MetricRow';
import { useGhostStore } from '../../../state/store';

export function DecisionInspector({ decisionId }: { decisionId: string }) {
  const d = useGhostStore((s) => s.decisions[decisionId]);
  const task = useGhostStore((s) => (d ? s.tasks[d.task_id] : undefined));

  if (!d) return null;

  return (
    <>
      <header className="inspector-header">
        <h2>Scheduler decision</h2>
      </header>
      <section className="scheduler-block">
        <h3>Resource</h3>
        <MetricRow label="Class" value={d.target_resource_class} />
        <MetricRow label="Priority" value={String(d.priority)} />
      </section>
      <section className="scheduler-block">
        <h3>Why</h3>
        <ul className="reason-codes">
          {d.reason_codes.map((code) => (
            <li key={code}>{code}</li>
          ))}
        </ul>
        {d.notes && <p className="muted">{d.notes}</p>}
      </section>
      <MetricRow label="Est. runtime" value={`${d.cpu_runtime_sec ?? d.gpu_runtime_sec ?? '—'}s`} />
      <MetricRow label="PROJECTED (sched)" value={`$${d.estimated_cost_usd.toFixed(4)}`} />
      {task && <MetricRow label="Task" value={task.label ?? task.id} />}
    </>
  );
}
