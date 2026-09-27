import { colors } from '../materials/theme';

export function VerifierProbe({ position = [0, 0.3, 0] }: { position?: [number, number, number] }) {
  return (
    <group position={position}>
      <mesh>
        <torusGeometry args={[0.1, 0.015, 8, 24]} />
        <meshStandardMaterial color={colors.mint} />
      </mesh>
      <mesh>
        <sphereGeometry args={[0.04, 8, 8]} />
        <meshBasicMaterial color={colors.mint} />
      </mesh>
    </group>
  );
}
