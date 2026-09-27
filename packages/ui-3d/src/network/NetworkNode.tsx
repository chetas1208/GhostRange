import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import type { Group, Mesh } from 'three';
import { SelectableGroup } from '../shared/SelectableGroup';
import type { InteractionState, NetworkNodeKind, NodeStatus } from '../types';
import { colors } from '../materials/theme';
import { NodeMeshBody } from './geometry/nodeMeshes';

export type NetworkNodeProps = {
  kind: NetworkNodeKind;
  position?: [number, number, number];
  status?: NodeStatus;
  interaction?: InteractionState;
  /** Legacy: maps to interaction selected */
  selected?: boolean;
  fractured?: boolean;
  onClick?: () => void;
  onPointerOver?: () => void;
  onPointerOut?: () => void;
};

export function NetworkNode({
  kind,
  position = [0, 0, 0],
  status = 'healthy',
  interaction,
  selected = false,
  fractured,
  onClick,
  onPointerOver,
  onPointerOut,
}: NetworkNodeProps) {
  const ripple = useRef(0);
  const group = useRef<Group>(null);
  const halo = useRef<Mesh>(null);

  const resolvedInteraction: InteractionState =
    interaction ?? (selected ? 'selected' : 'idle');

  useFrame((_, d) => {
    if (status === 'investigating') ripple.current += d * 2;
    if (status === 'under_attack' && group.current) {
      group.current.rotation.z = Math.sin(ripple.current) * 0.02;
      ripple.current += d * 4;
    }
    if (halo.current && status === 'investigating') {
      const s = 1.05 + Math.sin(ripple.current) * 0.02;
      halo.current.scale.set(s, s, s);
    }
  });

  const isCompromised = status === 'compromised' || fractured;
  const patching = status === 'patching';
  const verifying = status === 'verifying';

  return (
    <SelectableGroup
      position={position}
      interaction={resolvedInteraction}
      onClick={onClick}
      onPointerOver={onPointerOver}
      onPointerOut={onPointerOut}
    >
      <group ref={group}>
        <NodeMeshBody kind={kind} fractured={isCompromised} patching={patching} />
        {status === 'investigating' && (
          <mesh ref={halo}>
            <boxGeometry args={[0.55, 0.4, 0.45]} />
            <meshBasicMaterial color={colors.violet} wireframe transparent opacity={0.15} />
          </mesh>
        )}
        {verifying && (
          <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, 0.05, 0]}>
            <ringGeometry args={[0.28, 0.32, 24]} />
            <meshBasicMaterial color={colors.mint} transparent opacity={0.35} />
          </mesh>
        )}
        {status === 'failed' && (
          <mesh position={[0.05, 0, 0]}>
            <boxGeometry args={[0.48, 0.32, 0.38]} />
            <meshStandardMaterial color={colors.failure} wireframe opacity={0.5} transparent />
          </mesh>
        )}
      </group>
    </SelectableGroup>
  );
}

/** @deprecated use NetworkNodeKind */
export type NodeKind = NetworkNodeKind;
