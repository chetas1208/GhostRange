/** Quarantined contribution — out of active constellation (Agent 35). */
export function ContributionQuarantine() {
  return (
    <group name="contribution-quarantine" position={[2.2, -0.1, 0]}>
      <mesh>
        <boxGeometry args={[0.15, 0.15, 0.15]} />
        <meshStandardMaterial color="#ef4444" opacity={0.5} transparent />
      </mesh>
    </group>
  );
}
