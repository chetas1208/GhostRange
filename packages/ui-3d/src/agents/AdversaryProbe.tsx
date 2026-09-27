import { colors } from '../materials/theme';

export function AdversaryProbe({ position = [0, 0.3, 0] }: { position?: [number, number, number] }) {
  return (
    <mesh position={position} rotation={[0, 0, 0.4]}>
      <coneGeometry args={[0.07, 0.16, 3]} />
      <meshStandardMaterial color={colors.failure} emissive={colors.failure} emissiveIntensity={0.15} />
    </mesh>
  );
}
