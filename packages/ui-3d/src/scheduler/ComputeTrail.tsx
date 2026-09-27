import { colors } from '../materials/theme';

export type ComputeTrailProps = {
  points: [number, number, number][];
  intensity?: number;
};

export function ComputeTrail({ points, intensity = 0.5 }: ComputeTrailProps) {
  if (points.length < 2) return null;
  const flat = points.flat();
  return (
    <line>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={points.length}
          array={new Float32Array(flat)}
          itemSize={3}
        />
      </bufferGeometry>
      <lineBasicMaterial
        color={colors.amber}
        transparent
        opacity={0.15 + intensity * 0.35}
        linewidth={1 + intensity * 2}
      />
    </line>
  );
}
