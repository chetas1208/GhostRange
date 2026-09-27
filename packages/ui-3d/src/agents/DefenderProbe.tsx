import { colors } from '../materials/theme';

export function DefenderProbe({ position = [0, 0.3, 0] }: { position?: [number, number, number] }) {
  return (
    <mesh position={position}>
      <octahedronGeometry args={[0.1, 0]} />
      <meshStandardMaterial color={colors.mint} emissive={colors.mint} emissiveIntensity={0.12} />
    </mesh>
  );
}
