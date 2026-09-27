import { useFrame } from '@react-three/fiber';
import { useMemo, useRef } from 'react';
import type { BufferAttribute } from 'three';
import { colors } from '../materials/theme';
import type { LinkStatus } from '../types';

export type NetworkLinkProps = {
  from: [number, number, number];
  to: [number, number, number];
  status?: LinkStatus;
  activeTraffic?: boolean;
  attack?: boolean;
  faint?: boolean;
};

export function NetworkLink({
  from,
  to,
  status: statusProp,
  activeTraffic = false,
  attack = false,
  faint = false,
}: NetworkLinkProps) {
  const pulse = useRef(0);
  const attr = useRef<BufferAttribute>(null);
  const status: LinkStatus =
    statusProp ?? (attack ? 'attack' : faint ? 'faint' : activeTraffic ? 'active' : 'idle');

  const isAttack = status === 'attack';
  const faintLink = status === 'faint' || status === 'disabled';
  const color = isAttack ? colors.failure : status === 'active' ? colors.linkActive : colors.link;

  const points = useMemo(
    () =>
      new Float32Array([
        from[0],
        from[1],
        from[2],
        (from[0] + to[0]) / 2,
        (from[1] + to[1]) / 2,
        (from[2] + to[2]) / 2,
        to[0],
        to[1],
        to[2],
      ]),
    [from, to],
  );

  useFrame((_, d) => {
    if (status === 'attack' || activeTraffic) pulse.current += d * 2.5;
    if (!attr.current) return;
    const midY = (from[1] + to[1]) / 2 + (isAttack ? Math.sin(pulse.current) * 0.06 : 0);
    points[4] = midY;
    attr.current.needsUpdate = true;
  });

  return (
    <line>
      <bufferGeometry>
        <bufferAttribute ref={attr} attach="attributes-position" count={3} array={points} itemSize={3} />
      </bufferGeometry>
      <lineBasicMaterial
        color={color}
        transparent
        opacity={faintLink ? 0.15 : isAttack ? 0.85 : activeTraffic ? 0.7 : 0.5}
      />
    </line>
  );
}
