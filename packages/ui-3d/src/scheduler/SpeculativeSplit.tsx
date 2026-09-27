import { colors } from '../materials/theme';

export type SpeculativeSplitProps = {
  origin: [number, number, number];
  left: [number, number, number];
  right: [number, number, number];
  winnerSide?: 'left' | 'right' | null;
};

export function SpeculativeSplit({ origin, left, right, winnerSide }: SpeculativeSplitProps) {
  const leftOpacity = winnerSide === 'right' ? 0.2 : 1;
  const rightOpacity = winnerSide === 'left' ? 0.2 : 1;

  return (
    <group>
      <SplitLine from={origin} to={left} opacity={leftOpacity} />
      <SplitLine from={origin} to={right} opacity={rightOpacity} />
    </group>
  );
}

function SplitLine({
  from,
  to,
  opacity,
}: {
  from: [number, number, number];
  to: [number, number, number];
  opacity: number;
}) {
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
      <lineBasicMaterial color={colors.violet} transparent opacity={opacity} />
    </line>
  );
}
