import { useFrame } from '@react-three/fiber';
import { useRef, type ReactNode } from 'react';
import type { Group } from 'three';

type Props = {
  children: ReactNode;
  enabled?: boolean;
};

/** Slow orbit of child-world cluster; stops when reduced motion (--gr-motion-scale=0). */
export function MultiverseOrbitField({ children, enabled = true }: Props) {
  const ref = useRef<Group>(null);

  useFrame((_, delta) => {
    if (!enabled || !ref.current) return;
    const scale = parseFloat(
      getComputedStyle(document.documentElement).getPropertyValue('--gr-motion-scale') || '1',
    );
    if (scale <= 0) return;
    ref.current.rotation.y += delta * 0.04 * scale;
  });

  return <group ref={ref}>{children}</group>;
}
