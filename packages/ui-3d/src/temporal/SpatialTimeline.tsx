import { colors } from '../materials/theme';

export type TimelineMarker = {
  t: number;
  position: [number, number, number];
};

export type SpatialTimelineProps = {
  markers: TimelineMarker[];
  nowPosition?: [number, number, number];
};

export function SpatialTimeline({ markers, nowPosition = [3, -1.2, 0] }: SpatialTimelineProps) {
  if (markers.length === 0) return null;
  const pts = markers.flatMap((m) => m.position);
  return (
    <group position={[0, -2, 2]}>
      <line>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={markers.length}
            array={new Float32Array(pts)}
            itemSize={3}
          />
        </bufferGeometry>
        <lineBasicMaterial color={colors.link} transparent opacity={0.35} />
      </line>
      {markers.map((m, i) => (
        <mesh key={i} position={m.position}>
          <sphereGeometry args={[0.04, 8, 8]} />
          <meshBasicMaterial color={colors.linkActive} />
        </mesh>
      ))}
      <mesh position={nowPosition}>
        <sphereGeometry args={[0.07, 12, 12]} />
        <meshBasicMaterial color={colors.electric} />
      </mesh>
    </group>
  );
}
