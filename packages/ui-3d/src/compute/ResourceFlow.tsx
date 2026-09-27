import { colors } from '../materials/theme';

export type ResourceFlowProps = {
  from: [number, number, number];
  to: [number, number, number];
  thickness?: number;
};

export function ResourceFlow({ from, to, thickness = 0.02 }: ResourceFlowProps) {
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
      <lineBasicMaterial color={colors.violet} linewidth={thickness} transparent opacity={0.5} />
    </line>
  );
}
