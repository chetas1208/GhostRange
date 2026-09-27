import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import type { Group, Mesh, MeshStandardMaterial } from 'three';
import { colors } from '../materials/theme';
import { readMotionScale } from '../shared/motionScale';

export type GpuWorkerProps = {
  position?: [number, number, number];
  utilization?: number;
};

function GpuLed({ x, utilization, phase }: { x: number; utilization: number; phase: number }) {
  const mesh = useRef<Mesh>(null);
  const t = useRef(phase);

  useFrame((_, delta) => {
    if (!mesh.current) return;
    t.current += delta * readMotionScale();
    const mat = mesh.current.material as MeshStandardMaterial;
    const shimmer = 0.5 + Math.sin(t.current * 3) * 0.5;
    mat.emissiveIntensity = 0.15 + utilization * (0.35 + shimmer * 0.15);
  });

  return (
    <mesh ref={mesh} position={[x, 0.12, 0]}>
      <boxGeometry args={[0.04, 0.18, 0.42]} />
      <meshStandardMaterial color={colors.electric} emissive={colors.electric} emissiveIntensity={0.15} />
    </mesh>
  );
}

/**
 * A single GPU compute worker. A lone active GPU worker should read as a
 * substantial, live piece of infrastructure — gentle idle breathing on the
 * chassis plus a utilization-linked shimmer on each LED column give it
 * ambient life without inventing any status this component doesn't have
 * (status still lives entirely in what's passed down via ComputeNode).
 */
export function GpuWorker({ position = [0, 0, 0], utilization = 0 }: GpuWorkerProps) {
  const group = useRef<Group>(null);
  const t = useRef(0);

  useFrame((_, delta) => {
    if (!group.current) return;
    t.current += delta * readMotionScale();
    const breathe = 1 + Math.sin(t.current * 1.1) * 0.015;
    group.current.scale.set(breathe, breathe, breathe);
  });

  return (
    <group ref={group} position={position}>
      <mesh>
        <boxGeometry args={[0.6, 0.2 + utilization * 0.15, 0.5]} />
        <meshStandardMaterial color={colors.graphite} metalness={0.35} roughness={0.5} />
      </mesh>
      {[-0.18, -0.06, 0.06, 0.18].map((x, i) => (
        <GpuLed key={x} x={x} utilization={utilization} phase={i * 1.7} />
      ))}
    </group>
  );
}
