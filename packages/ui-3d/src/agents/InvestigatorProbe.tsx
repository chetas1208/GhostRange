import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import type { Mesh } from 'three';
import { colors } from '../materials/theme';

export function InvestigatorProbe({ position = [0, 0.3, 0] }: { position?: [number, number, number] }) {
  const phase = useRef(0);
  const mesh = useRef<Mesh>(null);

  useFrame((_, d) => {
    phase.current += d;
    if (mesh.current) {
      mesh.current.position.set(
        position[0],
        position[1] + Math.sin(phase.current * 2) * 0.05,
        position[2],
      );
    }
  });

  return (
    <mesh ref={mesh} position={position}>
      <coneGeometry args={[0.08, 0.14, 3]} />
      <meshStandardMaterial color={colors.violet} emissive={colors.violet} emissiveIntensity={0.2} />
    </mesh>
  );
}
