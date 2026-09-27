import { ResourceFlow } from '../compute/ResourceFlow';

export type SchedulerDecisionProps = {
  from: [number, number, number];
  to: [number, number, number];
  visible?: boolean;
};

export function SchedulerDecision({ from, to, visible = true }: SchedulerDecisionProps) {
  if (!visible) return null;
  return <ResourceFlow from={from} to={to} thickness={0.03} />;
}
