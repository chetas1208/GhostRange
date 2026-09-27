import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import type { Mesh } from 'three';
import { colors } from '../materials/theme';

export type WorldCollapseProps = {
  active?: boolean;
  onComplete?: () => void;
};

/** Failed world contracts to evidence shard. */
export function WorldCollapse({ active = false, onComplete }: WorldCollapseProps) {
  const scale = useRef(1);
  const mesh = useRef<Mesh>(null);
  const completed = useRef(false);

  useFrame((_, d) => {
    if (!active || !mesh.current) return;
    scale.current = Math.max(0.08, scale.current - d * 0.4);
    mesh.current.scale.setScalar(scale.current);
    if (scale.current <= 0.09 && !completed.current) {
      completed.current = true;
      onComplete?.();
    }
  });

  if (!active) return null;

  return (
    <mesh ref={mesh}>
      <octahedronGeometry args={[0.12, 0]} />
      <meshStandardMaterial color={colors.failure} emissive={colors.failure} emissiveIntensity={0.3} />
    </mesh>
  );
}
