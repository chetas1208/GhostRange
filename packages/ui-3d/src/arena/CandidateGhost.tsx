export function CandidateGhost(_props: { version: string }) {
  return (
    <mesh position={[2, 0.5, 0]}>
      <capsuleGeometry args={[0.25, 0.6, 4, 8]} />
      <meshStandardMaterial color="#4299e1" />
    </mesh>
  );
}
