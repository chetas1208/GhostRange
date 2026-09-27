export function RegressionBreak(_props: { dimension: string }) {
  return (
    <mesh position={[0, 1.5, 0]}>
      <boxGeometry args={[1.8, 0.15, 0.15]} />
      <meshStandardMaterial color="#c53030" />
    </mesh>
  );
}
