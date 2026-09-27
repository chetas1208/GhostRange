import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import { colors } from '../materials/theme';
import type { AttackPathState } from '../types';

export type AttackPathProps = {
  points: [number, number, number][];
  state?: AttackPathState;
  /** Legacy: active pulse when true */
  active?: boolean;
};

export function AttackPath({ points, state: stateProp, active = false }: AttackPathProps) {
  const state: AttackPathState =
    stateProp ?? (active ? 'active' : 'historical');
  const t = useRef(0);
  useFrame((_, d) => {
    if (state === 'active') t.current += d;
  });

  if (points.length < 2) return null;

  const flat: number[] = [];
  for (const p of points) flat.push(...p);

  const opacity =
    state === 'historical' ? 0.12 : state === 'planned' ? 0.25 : state === 'blocked' ? 0.4 : 0.75;
  const color = state === 'blocked' ? colors.amber : colors.failure;

  return (
    <group>
      <line>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={points.length}
            array={new Float32Array(flat)}
            itemSize={3}
          />
        </bufferGeometry>
        <lineBasicMaterial color={color} transparent opacity={opacity} />
      </line>
      {(state === 'active' || state === 'succeeded') && (
        <mesh position={points[points.length - 1]}>
          <sphereGeometry args={[state === 'succeeded' ? 0.04 : 0.06, 8, 8]} />
          <meshBasicMaterial color={color} transparent opacity={opacity} />
        </mesh>
      )}
    </group>
  );
}
