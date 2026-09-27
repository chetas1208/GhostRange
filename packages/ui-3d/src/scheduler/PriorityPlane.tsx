/** Visual guide plane for priority elevation (low priority farther). */
export function PriorityPlane({ z = -2 }: { z?: number }) {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.5, z]}>
      <planeGeometry args={[12, 6]} />
      <meshBasicMaterial color="#1a1a20" transparent opacity={0.08} />
    </mesh>
  );
}
