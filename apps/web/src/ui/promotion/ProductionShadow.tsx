/**
 * Non-executable reference geometry for proposed production topology.
 * Distinct from live GhostRange worlds — no production control surface.
 */
import { useMemo } from 'react';
import * as THREE from 'three';

type Props = {
  alignedComponentIds?: string[];
  changedComponentIds?: string[];
};

export function ProductionShadow({ alignedComponentIds = [], changedComponentIds = ['auth-service'] }: Props) {
  const positions = useMemo(() => {
    const ids = [...new Set([...alignedComponentIds, ...changedComponentIds])];
    return ids.map((id, i) => ({
      id,
      pos: new THREE.Vector3((i - ids.length / 2) * 1.2, 0.15, -2.5),
      changed: changedComponentIds.includes(id),
    }));
  }, [alignedComponentIds, changedComponentIds]);

  return (
    <group name="production-shadow" userData={{ nonExecutable: true }}>
      {positions.map(({ id, pos, changed }) => (
        <mesh key={id} position={pos}>
          <boxGeometry args={[0.9, 0.35, 0.9]} />
          <meshStandardMaterial
            color={changed ? '#c47aff' : '#4a5568'}
            transparent
            opacity={changed ? 0.85 : 0.35}
            wireframe={!changed}
          />
        </mesh>
      ))}
    </group>
  );
}
