export function BudgetEnvelope({ spentUsd, capUsd }: { spentUsd: number; capUsd: number }) {
  const ratio = capUsd > 0 ? Math.min(1, spentUsd / capUsd) : 0;
  return (
    <mesh position={[0, -1, 0]} scale={[ratio, 1, 1]}>
      <boxGeometry args={[3, 0.12, 0.12]} />
      <meshStandardMaterial color={ratio > 0.9 ? '#dd6b20' : '#4a5568'} />
    </mesh>
  );
}
