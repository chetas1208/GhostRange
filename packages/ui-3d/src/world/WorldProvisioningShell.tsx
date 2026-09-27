import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import type { Mesh } from 'three';
import { useSemanticMotion } from '../hooks/useSemanticMotion';
import { colors } from '../materials/theme';

export type WorldProvisioningShellProps = {
  width?: number;
  depth?: number;
};

/** Translucent shell — world exists only after world.provisioning. No topology inside. */
export function WorldProvisioningShell({ width = 4, depth = 3 }: WorldProvisioningShellProps) {
  const motion = useSemanticMotion('provisioning');
  const plane = useRef<Mesh>(null);
  const ring = useRef<Mesh>(null);

  useFrame(() => {
    const pulse = motion.current.pulse;
    if (plane.current) {
      const mat = plane.current.material;
      if (mat && 'opacity' in mat && typeof mat.opacity === 'number') {
        mat.opacity = 0.08 + pulse * 0.06;
      }
    }
    if (ring.current) {
      ring.current.scale.set(1, 1 + pulse * 0.2, 1);
    }
  });

  return (
    <group>
      <mesh ref={plane} rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, 0]}>
        <planeGeometry args={[width, depth]} />
        <meshStandardMaterial
          color={colors.electric}
          transparent
          opacity={0.08}
          wireframe
          emissive={colors.electric}
          emissiveIntensity={0.12}
        />
      </mesh>
      <mesh ref={ring} rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
        <ringGeometry args={[0.4, 0.45, 32]} />
        <meshBasicMaterial color={colors.electric} transparent opacity={0.2} />
      </mesh>
    </group>
  );
}
