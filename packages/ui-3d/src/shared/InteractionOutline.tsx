import { colors } from '../materials/theme';
import type { InteractionState } from '../types';

export type InteractionOutlineProps = {
  state?: InteractionState;
  width?: number;
  height?: number;
  depth?: number;
};

export function InteractionOutline({
  state = 'idle',
  width = 0.65,
  height = 0.55,
  depth = 0.65,
}: InteractionOutlineProps) {
  if (state === 'idle' || state === 'disabled') return null;

  const opacity =
    state === 'selected' || state === 'focused' ? 0.45 : state === 'hovered' ? 0.28 : 0.2;
  const color = state === 'error' ? colors.failure : state === 'stale' ? colors.link : colors.selection;

  return (
    <mesh scale={1.18}>
      <boxGeometry args={[width, height, depth]} />
      <meshBasicMaterial color={color} wireframe transparent opacity={opacity} />
    </mesh>
  );
}
