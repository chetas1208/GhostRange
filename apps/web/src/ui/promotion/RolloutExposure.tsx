/** Generic exposure indicator — not hard-coded 10/25/50/100. */
type Props = { exposureLabel: string; solidFraction?: number };

export function RolloutExposure({ solidFraction = 0.05 }: Props) {
  const pct = Math.round(Math.min(1, Math.max(0, solidFraction)) * 100);
  return (
    <group name="rollout-exposure" userData={{ observational: true }}>
      <mesh position={[0, 0.05, -2.2]}>
        <boxGeometry args={[0.4 + pct / 100, 0.2, 0.4 + pct / 100]} />
        <meshStandardMaterial transparent opacity={0.35 + pct / 200} color="#6ee7b7" />
      </mesh>
      {/* exposureLabel rendered in DOM inspector — avoid 3D text */}
    </group>
  );
}
