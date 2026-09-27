export type ArenaRunProps = {
  baselineVersion: string;
  candidateVersion: string;
  budgetLabel: string;
  progress: number;
};

export function ArenaRun({ progress }: ArenaRunProps) {
  const t = Math.min(1, Math.max(0, progress));
  return (
    <group name="ArenaRun">
      <mesh position={[-1.5, 0.2, 0]}>
        <boxGeometry args={[0.6, 0.6, 0.6]} />
        <meshStandardMaterial color="#4a5568" />
      </mesh>
      <mesh position={[1.5, 0.2, 0]}>
        <boxGeometry args={[0.6, 0.6, 0.6]} />
        <meshStandardMaterial color="#3182ce" />
      </mesh>
      <mesh position={[0, 1.2, 0]} scale={[t, 1, 1]}>
        <boxGeometry args={[3, 0.08, 0.08]} />
        <meshStandardMaterial color="#ecc94b" />
      </mesh>
    </group>
  );
}
