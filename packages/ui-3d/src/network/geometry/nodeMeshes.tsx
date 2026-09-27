import { useFrame } from '@react-three/fiber';
import type { ReactNode } from 'react';
import { useRef } from 'react';
import type { Group } from 'three';
import { colors } from '../../materials/theme';
import type { NetworkNodeKind } from '../../types';

function PatchingSkew({ children, active }: { children: ReactNode; active?: boolean }) {
  const g = useRef<Group>(null);
  useFrame(() => {
    if (!active || !g.current) return;
    g.current.rotation.z = Math.sin(performance.now() * 0.002) * 0.04;
    g.current.position.x = Math.sin(performance.now() * 0.003) * 0.02;
  });
  return <group ref={g}>{children}</group>;
}

export function NodeMeshBody({
  kind,
  fractured,
  patching,
}: {
  kind: NetworkNodeKind;
  fractured?: boolean;
  patching?: boolean;
}) {
  const skew = fractured ? 0.08 : 0;
  const body = (() => {
    switch (kind) {
      case 'internet':
        return (
          <mesh rotation={[Math.PI / 2, 0, 0]}>
            <torusGeometry args={[0.35, 0.02, 8, 32]} />
            <meshStandardMaterial color={colors.link} wireframe />
          </mesh>
        );
      case 'gateway':
        return (
          <mesh rotation={[0, Math.PI / 6, skew]}>
            <cylinderGeometry args={[0.35, 0.35, 0.2, 6]} />
            <meshStandardMaterial color={colors.surface} metalness={0.15} roughness={0.8} />
          </mesh>
        );
      case 'vm':
      case 'compute_mapped':
        return (
          <mesh position={[skew, 0, 0]}>
            <boxGeometry args={[0.5, 0.35, 0.4]} />
            <meshStandardMaterial color={colors.surface} metalness={0.25} roughness={0.65} />
          </mesh>
        );
      case 'container':
        return (
          <group>
            {[0, 0.12, 0.24].map((y, i) => (
              <mesh key={i} position={[0, y, 0]}>
                <boxGeometry args={[0.28, 0.1, 0.28]} />
                <meshStandardMaterial color={colors.graphite} />
              </mesh>
            ))}
          </group>
        );
      case 'service':
        return (
          <mesh>
            <cylinderGeometry args={[0.12, 0.12, 0.45, 12]} />
            <meshStandardMaterial color={colors.electric} emissive={colors.electric} emissiveIntensity={0.12} />
          </mesh>
        );
      case 'database':
        return (
          <group>
            {[0, 0.08, 0.16].map((y, i) => (
              <mesh key={i} position={[0, y, 0]}>
                <cylinderGeometry args={[0.22 - i * 0.02, 0.22 - i * 0.02, 0.08, 16]} />
                <meshStandardMaterial color={colors.graphite} metalness={0.1} />
              </mesh>
            ))}
          </group>
        );
      case 'auth':
        return (
          <mesh rotation={[0, Math.PI / 8, skew]}>
            <cylinderGeometry args={[0.25, 0.25, 0.3, 8]} />
            <meshStandardMaterial color={colors.violet} emissive={colors.violet} emissiveIntensity={0.1} />
          </mesh>
        );
      case 'gpu':
        return (
          <mesh>
            <boxGeometry args={[0.55, 0.15, 0.45]} />
            <meshStandardMaterial color={colors.graphite} />
          </mesh>
        );
      default:
        return (
          <mesh>
            <boxGeometry args={[0.3, 0.3, 0.3]} />
            <meshStandardMaterial color={colors.graphite} />
          </mesh>
        );
    }
  })();

  if (patching && !fractured) return <PatchingSkew active>{body}</PatchingSkew>;
  return body;
}
