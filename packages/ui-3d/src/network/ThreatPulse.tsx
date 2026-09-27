import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import type { Mesh } from 'three';
import { colors } from '../materials/theme';

export type ThreatPulseProps = {
  position?: [number, number, number];
  active?: boolean;
  duration?: number;
};

/** Bounded, event-driven pulse at exploit/attack transition. */
export function ThreatPulse({ position = [0, 0, 0], active = true, duration = 1.2 }: ThreatPulseProps) {
  const t = useRef(0);
  const mesh = useRef<Mesh>(null);
  const done = useRef(false);

  useFrame((_, d) => {
    if (!active) return;
    if (done.current) return;
    t.current = Math.min(duration, t.current + d);
    const scale = 0.3 + (t.current / duration) * 0.8;
    const opacity = (1 - t.current / duration) * 0.45;
    if (mesh.current) {
      mesh.current.scale.setScalar(scale);
      const mat = mesh.current.material;
      if (mat && 'opacity' in mat && typeof mat.opacity === 'number') mat.opacity = opacity;
    }
    if (t.current >= duration) done.current = true;
  });

  if (!active) return null;

  return (
    <mesh ref={mesh} position={position}>
      <sphereGeometry args={[0.12, 12, 12]} />
      <meshBasicMaterial color={colors.failure} transparent opacity={0.45} />
    </mesh>
  );
}
