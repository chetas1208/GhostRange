export type QualificationGateProps = {
  recommendation: 'QUALIFIED' | 'NOT_QUALIFIED' | 'INSUFFICIENT_EVIDENCE';
  safetyRegression?: boolean;
};

export function QualificationGate({ recommendation, safetyRegression }: QualificationGateProps) {
  const blocked = recommendation !== 'QUALIFIED' || safetyRegression;
  return (
    <group name="QualificationGate">
      <mesh position={[0, 2, 0]}>
        <boxGeometry args={[2.4, 0.3, 0.2]} />
        <meshStandardMaterial color={blocked ? '#8b2635' : '#2d6a4f'} />
      </mesh>
    </group>
  );
}
