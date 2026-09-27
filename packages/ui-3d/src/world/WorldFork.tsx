import { useFrame } from '@react-three/fiber';
import { useMemo, useRef } from 'react';
import type { Group } from 'three';
import { colors } from '../materials/theme';

export type WorldForkProps = {
  from: [number, number, number];
  to: [number, number, number];
  progress?: number;
  fill?: number;
};

export function WorldFork({ from, to, progress = 0, fill = 0.15 }: WorldForkProps) {
  const anim = useRef(progress);
  const head = useRef<Group>(null);
  const positions = useMemo(() => new Float32Array(6), []);

  useFrame((_, d) => {
    if (progress < 1) anim.current = Math.min(progress > 0 ? progress : 1, anim.current + d * 0.6);
    else anim.current = progress;

    const t = anim.current;
    const x = from[0] + (to[0] - from[0]) * t;
    const y = from[1] + (to[1] - from[1]) * t;
    const z = from[2] + (to[2] - from[2]) * t;

    positions[0] = from[0];
    positions[1] = from[1];
    positions[2] = from[2];
    positions[3] = x;
    positions[4] = y;
    positions[5] = z;

    if (head.current) {
      head.current.position.set(x, y, z);
      head.current.scale.setScalar(0.5 + fill * 0.5);
    }
  });

  return (
    <group>
      <line>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" count={2} array={positions} itemSize={3} />
        </bufferGeometry>
        <lineBasicMaterial color={colors.link} transparent opacity={0.35 + fill * 0.4} />
      </line>
      <group ref={head}>
        <mesh>
          <sphereGeometry args={[0.08, 8, 8]} />
          <meshStandardMaterial color={colors.electric} transparent opacity={0.25 + fill * 0.5} />
        </mesh>
      </group>
    </group>
  );
}
