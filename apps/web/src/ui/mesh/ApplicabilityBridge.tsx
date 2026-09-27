/** Lightweight bridge from abstract MeshSignal to local twin (Agent 33). */
type Props = { active: boolean };

export function ApplicabilityBridge({ active }: Props) {
  if (!active) return null;
  return (
    <group name="applicability-bridge">
      <mesh position={[0.9, 0.2, 0]}>
        <cylinderGeometry args={[0.02, 0.02, 0.6, 8]} />
        <meshStandardMaterial color="#34d399" opacity={0.6} transparent />
      </mesh>
    </group>
  );
}
