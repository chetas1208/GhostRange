import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import type { Group } from 'three';
import { colors } from '../materials/theme';

export type ServerlessInferenceNodeProps = {
  position?: [number, number, number];
  active?: boolean;
};

export function ServerlessInferenceNode({ position = [0, 0, 0], active = false }: ServerlessInferenceNodeProps) {
  const group = useRef<Group>(null);

  useFrame(() => {
    if (!group.current || !active) return;
    group.current.position.y = position[1] + Math.sin(performance.now() * 0.001) * 0.03;
  });

  return (
    <group ref={group} position={position}>
      <mesh>
        <octahedronGeometry args={[0.14, 0]} />
        <meshStandardMaterial
          color={colors.violet}
          transparent
          opacity={0.85}
          emissive={colors.violet}
          emissiveIntensity={active ? 0.25 : 0.08}
        />
      </mesh>
    </group>
  );
}
