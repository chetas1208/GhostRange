import { colors } from '../materials/theme';
import type { DependencyState } from '../types';

export type DependencyEdgeProps = {
  from: [number, number, number];
  to: [number, number, number];
  state?: DependencyState;
};

export function DependencyEdge({ from, to, state = 'unresolved' }: DependencyEdgeProps) {
  const color =
    state === 'fulfilled'
      ? colors.mint
      : state === 'failed'
        ? colors.failure
        : state === 'ready'
          ? colors.electric
          : colors.link;
  const opacity = state === 'unresolved' ? 0.25 : state === 'ready' ? 0.65 : 0.7;

  return (
    <line>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={2}
          array={new Float32Array([...from, ...to])}
          itemSize={3}
        />
      </bufferGeometry>
      <lineBasicMaterial color={color} transparent opacity={opacity} />
    </line>
  );
}
