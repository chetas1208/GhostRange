import { useFrame } from '@react-three/fiber';
import type { ReactNode } from 'react';
import { useRef } from 'react';
import type { Group } from 'three';

export type WorkerTerminationProps = {
  active?: boolean;
  children: ReactNode;
};

export function WorkerTermination({ active, children }: WorkerTerminationProps) {
  const sy = useRef(1);
  const group = useRef<Group>(null);

  useFrame((_, d) => {
    if (active) sy.current = Math.max(0, sy.current - d * 1.2);
    if (group.current) group.current.scale.set(1, sy.current, 1);
  });

  return <group ref={group}>{children}</group>;
}
