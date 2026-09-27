import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import type { Mesh } from 'three';
import { colors } from '../materials/theme';
import type { VerificationRingState } from '../types';

export type VerificationRingProps = {
  radius?: number;
  state?: VerificationRingState;
};

export function VerificationRing({ radius = 0.35, state = 'running' }: VerificationRingProps) {
  const t = useRef(0);
  const ring = useRef<Mesh>(null);

  const color =
    state === 'passed'
      ? colors.mint
      : state === 'failed'
        ? colors.failure
        : state === 'pending'
          ? colors.link
          : colors.mint;
  const baseOpacity =
    state === 'pending' ? 0.2 : state === 'failed' ? 0.65 : state === 'passed' ? 0.55 : 0.5;

  useFrame((_, d) => {
    if (state === 'running') t.current += d;
    if (ring.current) {
      const s = 1 + (state === 'running' ? Math.sin(t.current * 2) * 0.03 : 0) / radius;
      ring.current.scale.set(s, s, s);
    }
  });

  return (
    <mesh ref={ring} rotation={[Math.PI / 2, 0, 0]}>
      <torusGeometry args={[radius, 0.015, 8, 32]} />
      <meshBasicMaterial color={color} transparent opacity={baseOpacity} />
    </mesh>
  );
}
