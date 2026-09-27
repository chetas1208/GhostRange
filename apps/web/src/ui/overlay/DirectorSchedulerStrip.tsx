import { useMemo } from 'react';
import { useShallow } from 'zustand/react/shallow';
import { useGhostStore } from '../../state/store';

/** M10: WHAT TO TEST (Director) vs HOW TO RUN (Scheduler) — execution mode only. */
export function DirectorSchedulerStrip() {
  const { mode, log } = useGhostStore(
    useShallow((s) => ({
      mode: s.mode,
      log: s.eventLog.slice(-30),
    })),
  );

  const director = useMemo(
    () => log.filter((e) => e.type === 'director.decision' || e.type === 'golden_path.phase'),
    [log],
  );
  const scheduler = useMemo(() => log.filter((e) => e.type === 'scheduler.plan'), [log]);

  if (mode !== 'execution') return null;

  return (
    <div className="director-scheduler-strip" aria-label="Director and Scheduler layers">
      <section>
        <h3>GhostDirector — what to test</h3>
        <ul>
          {director.length === 0 && <li>Awaiting experiment selection events</li>}
          {director.map((e) => (
            <li key={e.id}>{e.label}</li>
          ))}
        </ul>
      </section>
      <section>
        <h3>GhostScheduler — how to execute</h3>
        <ul>
          {scheduler.length === 0 && <li>Awaiting scheduler plan events</li>}
          {scheduler.map((e) => (
            <li key={e.id}>{e.label}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
