/** Aggregated mesh patterns — LOD-friendly cluster (Agent 33). */
type Props = { count: number };

export function KnowledgeCluster({ count }: Props) {
  const scale = 0.2 + Math.min(count, 50) * 0.01;
  return (
    <group name="knowledge-cluster" userData={{ aggregate: true }}>
      <mesh scale={scale}>
        <icosahedronGeometry args={[0.35, 1]} />
        <meshStandardMaterial color="#6366f1" transparent opacity={0.25} />
      </mesh>
    </group>
  );
}
