import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import type { Mesh } from 'three';
import type { TaskStatus } from '../types';
import { colors } from '../materials/theme';

export type ExecutionTaskProps = {
  position?: [number, number, number];
  status: TaskStatus;
  priority?: number;
  label?: string;
  selected?: boolean;
  onClick?: () => void;
};

function statusColor(status: TaskStatus): string {
  switch (status) {
    case 'RUNNING':
      return colors.electric;
    case 'BLOCKED':
      return colors.amber;
    case 'FAILED':
      return colors.failure;
    case 'COMPLETED':
      return colors.mint;
    case 'SPECULATED':
      return colors.violet;
    default:
      return colors.surface;
  }
}

export function ExecutionTask({
  position = [0, 0, 0],
  status,
  priority = 0,
  selected,
  onClick,
}: ExecutionTaskProps) {
  const yBoost = (priority / 100) * 0.8;
  const mesh = useRef<Mesh>(null);
  const pulse = useRef(0);

  useFrame((_, d) => {
    if (status === 'RUNNING' && mesh.current) {
      pulse.current += d * 3;
      mesh.current.scale.y = 1 + Math.sin(pulse.current) * 0.06;
    }
    if (status === 'BLOCKED' && mesh.current) {
      pulse.current += d * 2;
      mesh.current.position.x = position[0] + Math.sin(pulse.current) * 0.02;
    }
  });

  const opacity =
    status === 'CANCELLED'
      ? 0.25
      : status === 'SPECULATED'
        ? 0.55
        : status === 'CREATED' || status === 'QUEUED'
          ? 0.65
          : 1;
  const wireframe = status === 'CREATED' || status === 'QUEUED';

  return (
    <mesh
      ref={mesh}
      position={[position[0], position[1] + yBoost, position[2]]}
      onClick={(e) => {
        e.stopPropagation();
        onClick?.();
      }}
    >
      <boxGeometry args={[0.35, 0.22, 0.28]} />
      <meshStandardMaterial
        color={statusColor(status)}
        transparent
        opacity={opacity}
        wireframe={wireframe}
        emissive={selected ? colors.selection : '#000'}
        emissiveIntensity={selected ? 0.25 : status === 'RUNNING' ? 0.12 : 0}
      />
    </mesh>
  );
}
