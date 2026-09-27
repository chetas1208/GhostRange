import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import type { Mesh } from 'three';
import { colors } from '../materials/theme';

export type ProvisioningGhostProps = {
  position?: [number, number, number];
  fill?: number;
};

export function ProvisioningGhost({ position = [0, 0, 0], fill = 0.3 }: ProvisioningGhostProps) {
  const pulse = useRef(0);
  const mesh = useRef<Mesh>(null);

  useFrame((_, d) => {
    pulse.current += d * 2;
    const mat = mesh.current?.material;
    if (mat && 'opacity' in mat && typeof mat.opacity === 'number') {
      mat.opacity = 0.35 + Math.sin(pulse.current) * 0.1;
    }
  });

  return (
    <group position={position}>
      <mesh ref={mesh} scale={[1, Math.max(0.05, fill), 1]}>
        <boxGeometry args={[0.55, 0.5, 0.45]} />
        <meshStandardMaterial
          color={colors.electric}
          wireframe
          transparent
          opacity={0.35}
          emissive={colors.electric}
          emissiveIntensity={0.2}
        />
      </mesh>
    </group>
  );
}
