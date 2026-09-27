import { colors } from '../materials/theme';

export type SchedulerDecisionMarkerProps = {
  position?: [number, number, number];
};

export function SchedulerDecisionMarker({ position = [0, 0, 0] }: SchedulerDecisionMarkerProps) {
  return (
    <mesh position={position}>
      <octahedronGeometry args={[0.05, 0]} />
      <meshStandardMaterial color={colors.violet} emissive={colors.violet} emissiveIntensity={0.2} />
    </mesh>
  );
}
