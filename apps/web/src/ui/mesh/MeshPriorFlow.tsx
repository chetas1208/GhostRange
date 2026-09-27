/** Execution tab — remote prior → Director → local world (Agent 34). */
type Props = { priorLabel: string };

export function MeshPriorFlow({ priorLabel }: Props) {
  return (
    <group name="mesh-prior-flow" userData={{ execution: true, prior: priorLabel }}>
      <mesh position={[-0.5, 0.15, 1]}>
        <sphereGeometry args={[0.08, 12, 12]} />
        <meshStandardMaterial color="#fbbf24" wireframe />
      </mesh>
    </group>
  );
}
