/** Local validation world fork — remote knowledge → local experiment (Agent 33). */
export function LocalValidationFork() {
  return (
    <group name="local-validation-fork" position={[0, 0, 0.8]}>
      <mesh>
        <coneGeometry args={[0.12, 0.25, 4]} />
        <meshStandardMaterial color="#22d3ee" />
      </mesh>
    </group>
  );
}
