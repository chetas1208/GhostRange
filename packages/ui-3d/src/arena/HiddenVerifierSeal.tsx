/** Placeholder mesh — verifier logic stays off-client / evaluator-only. */
export function HiddenVerifierSeal() {
  return (
    <mesh position={[0, -0.5, 0]}>
      <torusGeometry args={[0.8, 0.08, 8, 32]} />
      <meshStandardMaterial color="#2d3748" metalness={0.6} roughness={0.3} />
    </mesh>
  );
}
