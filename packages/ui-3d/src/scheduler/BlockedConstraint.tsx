import { colors } from '../materials/theme';

export type BlockedConstraintProps = {
  at: [number, number, number];
  height?: number;
};

export function BlockedConstraint({ at, height = 0.6 }: BlockedConstraintProps) {
  return (
    <mesh position={at}>
      <boxGeometry args={[0.06, height, 0.06]} />
      <meshStandardMaterial color={colors.amber} emissive={colors.amber} emissiveIntensity={0.2} />
    </mesh>
  );
}
