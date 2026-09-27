import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import type { Group, Mesh } from 'three';
import { useSemanticMotion } from '../hooks/useSemanticMotion';
import type { SemanticState } from '../materials/theme';
import { accentForState, colors } from '../materials/theme';
import type { WorldLifecycleStatus } from '../types';

export type WorldBoundaryProps = {
  width?: number;
  depth?: number;
  semanticState?: SemanticState;
  status?: WorldLifecycleStatus;
  opacity?: number;
  selected?: boolean;
  active?: boolean;
};

export function WorldBoundary({
  width = 4,
  depth = 3,
  semanticState = 'healthy',
  status = 'READY',
  opacity = 0.35,
  selected = false,
  active = true,
}: WorldBoundaryProps) {
  const motion = useSemanticMotion(semanticState);
  const root = useRef<Group>(null);
  const ring = useRef<Mesh>(null);
  const wireframe = status === 'REQUESTED';

  useFrame(() => {
    const { ripple, pulse } = motion.current;
    if (root.current) {
      root.current.scale.set(1 + ripple, 1, 1 + ripple);
    }
    if (ring.current) {
      ring.current.scale.set(0.55 + pulse * 0.9, 0.55 + pulse * 0.9, 1);
    }
  });

  if (status === 'DESTROYED') return null;

  return (
    <group ref={root}>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, 0]}>
        <planeGeometry args={[width, depth, 1, 1]} />
        <meshStandardMaterial
          color={colors.graphite}
          transparent
          opacity={active ? opacity : opacity * 0.5}
          metalness={0.08}
          roughness={0.88}
          wireframe={wireframe}
          emissive={selected ? accentForState(semanticState) : '#000000'}
          emissiveIntensity={selected ? 0.18 : 0}
        />
      </mesh>
      {(semanticState === 'verifying' || status === 'VERIFYING') && (
        <mesh ref={ring} rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
          <ringGeometry args={[0.55, 0.6, 40]} />
          <meshBasicMaterial color={colors.mint} transparent opacity={0.22} />
        </mesh>
      )}
    </group>
  );
}
