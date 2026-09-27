import { useFrame } from '@react-three/fiber';
import { useMemo, useRef } from 'react';
import type { InstancedMesh } from 'three';
import { Object3D } from 'three';
import { colors } from '../materials/theme';

const MAX = 48;

export type CostParticleProps = {
  intensity?: number;
  position?: [number, number, number];
};

/** Bounded cost trail particles (§17 / perf cap). */
export function CostParticle({ intensity = 0.3, position = [0, 0, 0] }: CostParticleProps) {
  const mesh = useRef<InstancedMesh>(null);
  const t = useRef(0);
  const active = Math.min(MAX, Math.max(0, Math.floor(intensity * MAX)));
  const dummy = useMemo(() => new Object3D(), []);

  useFrame((_, d) => {
    if (!mesh.current || active <= 0) return;
    t.current += d;
    for (let i = 0; i < active; i++) {
      const phase = t.current + i * 0.4;
      dummy.position.set(
        position[0] + Math.sin(phase) * 0.4,
        position[1] + (i / MAX) * 0.3 + Math.sin(phase * 2) * 0.05,
        position[2] + Math.cos(phase) * 0.3,
      );
      dummy.scale.setScalar(0.02 + intensity * 0.03);
      dummy.updateMatrix();
      mesh.current.setMatrixAt(i, dummy.matrix);
    }
    mesh.current.instanceMatrix.needsUpdate = true;
  });

  if (intensity <= 0.05) return null;

  return (
    <instancedMesh ref={mesh} args={[undefined, undefined, MAX]} position={position} frustumCulled={false}>
      <sphereGeometry args={[1, 6, 6]} />
      <meshBasicMaterial color={colors.electric} transparent opacity={0.35} />
    </instancedMesh>
  );
}
