import {
  BlockedConstraint,
  ComputeNode,
  ComputeTrail,
  CostParticle,
  DependencyEdge,
  ExecutionTask,
  PriorityPlane,
  ResourceFlow,
  SchedulerDecisionMarker,
  SpeculativeSplit,
  WorkerTermination,
  ActionGate,
  ActionPermit,
} from '@ghostrange/ui-3d';
import { useShallow } from 'zustand/react/shallow';
import { useGhostStore } from '../../state/store';
import { selectM2ExecutionTasks, selectTasks, selectWorkers } from '../../state/selectors';
import { TourAnchorTracker } from '../../tour/TourAnchorTracker';
import { useTourStore } from '../../tour/tourStore';

export function ExecutionScene() {
  const mode = useGhostStore((s) => s.mode);
  const tasks = useGhostStore(
    useShallow((s) => {
      const m2 = selectM2ExecutionTasks(s);
      return m2.length ? m2 : selectTasks(s);
    }),
  );
  const workers = useGhostStore(useShallow((s) => selectWorkers(s)));
  const decisionsRecord = useGhostStore((s) => s.decisions);
  const decisions = mode === 'execution' ? Object.values(decisionsRecord) : [];
  const selection = useGhostStore((s) => s.selection);
  const setSelection = useGhostStore((s) => s.setSelection);
  const totalCost = useGhostStore((s) => s.totalCostUsd);
  const authGate = useGhostStore((s) => s.authorizationGate);

  const tourOn = useTourStore((s) => s.isTourSession && s.status === 'RUNNING');

  if (mode !== 'execution') return null;

  const costIntensity = Math.min(1, totalCost / 0.5);

  const taskPos = (id: string): [number, number, number] => {
    const t = tasks.find((x) => x.id === id);
    const l = t?.layout;
    return [l?.x ?? 0, l?.y ?? 0.8, l?.z ?? 0];
  };

  const speculative = tasks.find((t) => t.status === 'SPECULATED');
  const primary = speculative ? tasks.find((t) => t.id === speculative.speculative_pair_id) : null;

  const mid = (a: [number, number, number], b: [number, number, number]): [number, number, number] => [
    (a[0] + b[0]) / 2,
    (a[1] + b[1]) / 2 + 0.15,
    (a[2] + b[2]) / 2,
  ];

  return (
    <group position={[0, 0, -8]}>
      <PriorityPlane />
      {tasks.map((t) =>
        t.dependencies.map((dep) => {
          const depTask = tasks.find((x) => x.id === dep);
          const state =
            depTask?.status === 'COMPLETED'
              ? 'fulfilled'
              : depTask?.status === 'FAILED'
                ? 'failed'
                : depTask?.status === 'RUNNING' || depTask?.status === 'SCHEDULED'
                  ? 'ready'
                  : 'unresolved';
          return (
            <DependencyEdge
              key={`${t.id}-${dep}`}
              from={taskPos(dep)}
              to={taskPos(t.id)}
              state={state}
            />
          );
        }),
      )}
      {tasks.map((t) => (
        <group key={t.id}>
          <ExecutionTask
            position={taskPos(t.id)}
            status={t.status}
            priority={t.priority ?? 50}
            selected={selection?.kind === 'task' && selection.id === t.id}
            onClick={() => setSelection({ kind: 'task', id: t.id })}
          />
          {t.blocked && <BlockedConstraint at={[taskPos(t.id)[0], taskPos(t.id)[1] - 0.2, taskPos(t.id)[2]]} />}
        </group>
      ))}
      {primary && speculative && (
        <SpeculativeSplit
          origin={taskPos(primary.id)}
          left={taskPos(primary.id)}
          right={taskPos(speculative.id)}
          winnerSide={primary.winner ? 'left' : speculative.winner ? 'right' : null}
        />
      )}
      {decisions.map((d) => {
        const task = tasks.find((t) => t.id === d.task_id);
        const worker = workers.find((w) => w.resource_class === d.target_resource_class);
        if (!task || !worker) return null;
        const wpos: [number, number, number] = [-3 + (worker.slot ?? 0) * 1.4, -1.2, 0];
        const from = taskPos(task.id);
        const marker = mid(from, wpos);
        const selected = selection?.kind === 'decision' && selection.id === d.id;
        return (
          <group key={d.id}>
            <ResourceFlow from={from} to={wpos} thickness={selected ? 0.05 : 0.03} />
            <group
              position={marker}
              onClick={(e) => {
                e.stopPropagation();
                setSelection({ kind: 'decision', id: d.id });
              }}
            >
              <SchedulerDecisionMarker />
            </group>
          </group>
        );
      })}
      <ComputeTrail
        points={tasks.filter((t) => t.status === 'RUNNING').map((t) => taskPos(t.id))}
        intensity={0.6}
      />
      <CostParticle intensity={costIntensity} position={[3, 0.2, 0]} />
      {authGate ? (
        <ActionGate
          position={authGate.position}
          state={authGate.state}
          actionType={authGate.actionType}
          reason={authGate.reason}
        />
      ) : null}
      {workers.some((w) => w.status === 'PROVISIONING' || w.status === 'REQUESTED') ? (
        <ActionPermit from={[0, 1.4, -8]} to={[-3, -0.6, -8]} active />
      ) : null}
      <group position={[0, -1.2, 0]}>
        {workers.map((w) => (
          <WorkerTermination key={w.id} active={w.terminating}>
            <group
              position={[-3 + (w.slot ?? 0) * 1.4, 0, 0]}
              onClick={(e) => {
                e.stopPropagation();
                setSelection({ kind: 'worker', id: w.id });
              }}
            >
              <ComputeNode
                resourceClass={w.resource_class}
                status={w.status}
                utilization={w.utilization}
              />
            </group>
          </WorkerTermination>
        ))}
      </group>
      {tourOn ? (
        <>
          <TourAnchorTracker anchorId="execution-dag" position={[1.2, 0.8, 0]} />
          <TourAnchorTracker anchorId="scheduler-decision" position={[2, 1, 0]} />
          <TourAnchorTracker anchorId="worker-active" position={[-3, 0, 0]} />
          <TourAnchorTracker anchorId="action-gate" position={[-2, 0.6, -8]} />
        </>
      ) : null}
    </group>
  );
}
