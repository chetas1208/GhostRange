/** Abstract remote knowledge — no tenant topology (M13). */
type Props = {
  knowledgeClass: string;
  tags: string[];
  disclosure: string;
  status: string;
};

export function MeshSignal({ tags }: Props) {
  const h = 0.15 + Math.min(tags.length, 6) * 0.04;
  return (
    <group name="mesh-signal" userData={{ observational: true, remote: true }}>
      <mesh position={[1.8, h, 0]}>
        <octahedronGeometry args={[0.12, 0]} />
        <meshStandardMaterial color="#a78bfa" wireframe />
      </mesh>
      {/* DOM inspector shows knowledgeClass, tags, disclosure, status — not contributor PII */}
    </group>
  );
}
