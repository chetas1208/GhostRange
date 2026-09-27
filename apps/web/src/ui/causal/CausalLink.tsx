type Props = { status: 'HYPOTHESIZED' | 'INTERVENTION_SUPPORTED' | 'REFUTED' };

export function CausalLink({ status }: Props) {
  const scale = status === 'INTERVENTION_SUPPORTED' ? 1.2 : status === 'REFUTED' ? 0.6 : 1;
  return (
    <group name="causal-link" scale={scale} userData={{ causalStatus: status }}>
      <mesh rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.015, 0.015, 0.5, 6]} />
        <meshStandardMaterial
          color={status === 'INTERVENTION_SUPPORTED' ? '#22c55e' : status === 'REFUTED' ? '#64748b' : '#eab308'}
          wireframe={status === 'HYPOTHESIZED'}
        />
      </mesh>
    </group>
  );
}
