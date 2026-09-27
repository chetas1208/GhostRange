import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import type { Group } from 'three';
import { colors } from '../materials/theme';
import type { ClaimState } from '../types';

export type ClaimNodeProps = {
  position?: [number, number, number];
  state?: ClaimState;
  /** Legacy booleans */
  anchored?: boolean;
  verified?: boolean;
  onClick?: () => void;
};

function claimColor(state: ClaimState): string {
  switch (state) {
    case 'verified':
      return colors.mint;
    case 'contradicted':
      return colors.failure;
    case 'partial':
      return colors.amber;
    case 'superseded':
      return colors.link;
    default:
      return colors.amber;
  }
}

export function ClaimNode({
  position = [0, 0, 0],
  state: stateProp,
  anchored = false,
  verified = false,
  onClick,
}: ClaimNodeProps) {
  const state: ClaimState =
    stateProp ?? (verified ? 'verified' : anchored ? 'partial' : 'unsupported');
  const drift = state === 'unsupported';
  const wobble = useRef(0);
  const group = useRef<Group>(null);

  useFrame((_, d) => {
    if (drift) wobble.current += d * 3;
    if (group.current) {
      group.current.position.x = position[0] + (drift ? Math.sin(wobble.current) * 0.08 : 0);
      group.current.position.y = position[1] + (drift ? Math.cos(wobble.current * 1.3) * 0.05 : 0);
      group.current.position.z = position[2];
    }
  });

  const emissiveIntensity =
    state === 'verified' ? 0.35 : state === 'contradicted' ? 0.25 : state === 'partial' ? 0.2 : 0.12;

  return (
    <group ref={group}>
      <mesh
        onClick={(e) => {
          e.stopPropagation();
          onClick?.();
        }}
        scale={state === 'superseded' ? 0.85 : 1}
      >
        <octahedronGeometry args={[0.2, 0]} />
        <meshStandardMaterial
          color={claimColor(state)}
          emissive={claimColor(state)}
          emissiveIntensity={emissiveIntensity}
          wireframe={state === 'unsupported'}
          transparent
          opacity={state === 'superseded' ? 0.5 : 1}
        />
      </mesh>
    </group>
  );
}
