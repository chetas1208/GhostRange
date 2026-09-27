export type EventMarkerProps = {
  position: [number, number, number];
  highlight?: boolean;
};

export function EventMarker({ position, highlight }: EventMarkerProps) {
  return (
    <mesh position={position}>
      <sphereGeometry args={[highlight ? 0.06 : 0.035, 8, 8]} />
      <meshBasicMaterial color={highlight ? '#60a5fa' : '#8b95a8'} />
    </mesh>
  );
}
