/** Revoked remote knowledge loses active prior link (Agent 35). */
export function RevocationBreak() {
  return (
    <group name="revocation-break">
      <mesh rotation={[0, 0, Math.PI / 4]}>
        <boxGeometry args={[0.5, 0.02, 0.02]} />
        <meshStandardMaterial color="#94a3b8" />
      </mesh>
    </group>
  );
}
