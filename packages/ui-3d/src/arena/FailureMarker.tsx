export type FailureMarkerProps = {
  stepIndex: number;
  failureType: string;
};

export function FailureMarker({ stepIndex }: FailureMarkerProps) {
  return (
    <group name="FailureMarker" position={[stepIndex * 0.4, 0.8, 0]}>
      <mesh>
        <octahedronGeometry args={[0.25, 0]} />
        <meshStandardMaterial color="#e53e3e" emissive="#742a2a" />
      </mesh>
    </group>
  );
}
