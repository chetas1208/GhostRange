type Props = { transportStatus: string };

export function TransportBridge({ transportStatus }: Props) {
  const broken = transportStatus === 'NOT_TRANSPORTABLE';
  return (
    <group name="transport-bridge">
      {!broken && (
        <mesh>
          <boxGeometry args={[0.6, 0.02, 0.02]} />
          <meshStandardMaterial color="#38bdf8" />
        </mesh>
      )}
      {broken && (
        <group name="transport-break">
          <mesh position={[-0.15, 0, 0]} rotation={[0, 0, 0.3]}>
            <boxGeometry args={[0.25, 0.02, 0.02]} />
            <meshStandardMaterial color="#94a3b8" />
          </mesh>
          <mesh position={[0.15, 0, 0]} rotation={[0, 0, -0.3]}>
            <boxGeometry args={[0.25, 0.02, 0.02]} />
            <meshStandardMaterial color="#94a3b8" />
          </mesh>
        </group>
      )}
    </group>
  );
}
