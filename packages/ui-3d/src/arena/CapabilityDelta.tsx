export function CapabilityDelta({ delta }: { delta: Record<string, number> }) {
  const keys = Object.keys(delta).slice(0, 4);
  return (
    <group name="CapabilityDelta">
      {keys.map((k, i) => (
        <mesh key={k} position={[i * 0.5 - 0.75, 2.2, 0]}>
          <boxGeometry args={[0.35, Math.max(0.1, delta[k]), 0.35]} />
          <meshStandardMaterial color={delta[k] >= 0 ? '#38a169' : '#e53e3e'} />
        </mesh>
      ))}
    </group>
  );
}
