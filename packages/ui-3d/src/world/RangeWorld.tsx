import type { ReactNode } from 'react';
import { WorldBoundary } from './WorldBoundary';
import { WorldStatusField } from './WorldStatusField';
import type { SemanticState } from '../materials/theme';
import type { WorldLifecycleStatus } from '../types';
import { worldLifecycleToSemantic } from './worldLifecycle';

export type RangeWorldProps = {
  worldId?: string;
  label?: string;
  subtitle?: string;
  position?: [number, number, number];
  status?: WorldLifecycleStatus;
  semanticState?: SemanticState;
  fill?: number;
  selected?: boolean;
  active?: boolean;
  collapsed?: boolean;
  dimmed?: boolean;
  children?: ReactNode;
};

export function RangeWorld({
  position = [0, 0, 0],
  status = 'READY',
  semanticState,
  fill = 1,
  selected = false,
  active = true,
  collapsed = false,
  dimmed = false,
  children,
}: RangeWorldProps) {
  if (collapsed) return null;

  const semantic = semanticState ?? worldLifecycleToSemantic(status);
  const opacityScale = dimmed ? 0.45 : 1;

  return (
    <group position={position} scale={[fill * opacityScale, fill * opacityScale, fill * opacityScale]}>
      <WorldBoundary
        semanticState={semantic}
        selected={selected}
        active={active}
        opacity={0.2 + fill * 0.3}
        status={status}
      />
      <WorldStatusField semanticState={semantic} />
      {children}
    </group>
  );
}
