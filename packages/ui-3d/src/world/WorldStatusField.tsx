import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import type { Mesh } from 'three';
import type { SemanticState } from '../materials/theme';
import { accentForState } from '../materials/theme';
import { useSemanticMotion } from '../hooks/useSemanticMotion';

export type WorldStatusFieldProps = {
  semanticState: SemanticState;
  radius?: number;
};

export function WorldStatusField({ semanticState, radius = 2.2 }: WorldStatusFieldProps) {
  const motion = useSemanticMotion(semanticState);
  const mesh = useRef<Mesh>(null);
  const color = accentForState(semanticState);

  useFrame(() => {
    if (!mesh.current) return;
    const { pulse, fracture } = motion.current;
    mesh.current.scale.set(1 - fracture, 1 - fracture, 1);
    const mat = mesh.current.material;
    if (mat && 'opacity' in mat && typeof mat.opacity === 'number') {
      mat.opacity = semanticState === 'verifying' ? 0.2 + pulse * 0.15 : 0.12;
    }
  });

  if (semanticState === 'healthy' || semanticState === 'verified') return null;

  return (
    <mesh ref={mesh} rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]}>
      <ringGeometry args={[radius, radius + 0.04, 48]} />
      <meshBasicMaterial color={color} transparent opacity={0.12} />
    </mesh>
  );
}
