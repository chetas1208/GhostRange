import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import type { Mesh, MeshStandardMaterial } from 'three';
import { colors } from '../materials/theme';
import { readMotionScale } from '../shared/motionScale';

export type CpuWorkerProps = {
  position?: [number, number, number];
  utilization?: number;
  label?: string;
};

/**
 * A single CPU compute worker. Given a real, sparse fleet (as few as one
 * live worker) is the common case, not the exception, this reads as
 * substantial on its own: a lit accent strip instead of a bare flat box,
 * and a subtle idle breathing/utilization pulse (§ ambient motion,
 * INTERACTION_MODEL.md's "motion is decoration, not the only channel for
 * information" — status still lives entirely in color/material, this only
 * adds life to it).
 */
export function CpuWorker({ position = [0, 0, 0], utilization = 0 }: CpuWorkerProps) {
  const h = 0.35 + utilization * 0.25;
  const body = useRef<Mesh>(null);
  const accent = useRef<Mesh>(null);
  const t = useRef(0);

  useFrame((_, delta) => {
    t.current += delta * readMotionScale();
    const breathe = 1 + Math.sin(t.current * 1.1) * 0.015;
    const pulse = 0.5 + Math.sin(t.current * 2.4) * 0.5;

    if (body.current) {
      body.current.scale.set(breathe, h * breathe, breathe);
      const mat = body.current.material as MeshStandardMaterial;
      mat.emissiveIntensity = 0.05 + utilization * (0.2 + pulse * 0.1);
    }
    if (accent.current) {
      const mat = accent.current.material as MeshStandardMaterial;
      mat.emissiveIntensity = 0.25 + utilization * 0.3 + pulse * 0.15;
    }
  });

  return (
    <group position={position}>
      <mesh ref={body}>
        <boxGeometry args={[0.5, 0.5, 0.45]} />
        <meshStandardMaterial
          color={colors.surface}
          metalness={0.3}
          roughness={0.55}
          emissive={colors.electric}
          emissiveIntensity={0.05}
        />
      </mesh>
      <mesh ref={accent} position={[0, h * 0.5 + 0.01, 0]}>
        <boxGeometry args={[0.52, 0.02, 0.47]} />
        <meshStandardMaterial
          color={colors.electric}
          emissive={colors.electric}
          emissiveIntensity={0.25}
          transparent
          opacity={0.6}
        />
      </mesh>
    </group>
  );
}
