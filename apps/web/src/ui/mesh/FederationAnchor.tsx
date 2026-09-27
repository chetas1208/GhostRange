/** Federation membership anchor — no remote topology (Agent 33). */
export function FederationAnchor() {
  return (
    <group name="federation-anchor" position={[-1.8, 0.3, 0]}>
      <mesh>
        <torusGeometry args={[0.12, 0.03, 8, 24]} />
        <meshStandardMaterial color="#64748b" />
      </mesh>
    </group>
  );
}
