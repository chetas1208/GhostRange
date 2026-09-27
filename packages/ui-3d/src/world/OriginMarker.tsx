import { colors } from '../materials/theme';

/** Faint origin when Multiverse chamber is empty. */
export function OriginMarker() {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]}>
      <ringGeometry args={[0.15, 0.2, 32]} />
      <meshBasicMaterial color={colors.link} transparent opacity={0.2} />
    </mesh>
  );
}
