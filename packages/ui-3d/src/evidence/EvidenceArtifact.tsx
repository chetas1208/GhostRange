import { DoubleSide } from 'three';
import type { ArtifactType } from '../types';
import { colors } from '../materials/theme';

export type EvidenceArtifactProps = {
  artifactType: ArtifactType;
  position?: [number, number, number];
  selected?: boolean;
  onClick?: () => void;
};

function ArtifactGeometry({ type }: { type: ArtifactType }) {
  switch (type) {
    case 'PCAP':
      return (
        <group rotation={[0.3, 0.5, 0.2]}>
          <mesh>
            <boxGeometry args={[0.14, 0.06, 0.1]} />
            <meshStandardMaterial color={colors.violet} />
          </mesh>
        </group>
      );
    case 'SCREENSHOT':
      return (
        <mesh rotation={[0.2, 0.4, 0]}>
          <planeGeometry args={[0.12, 0.08]} />
          <meshStandardMaterial color={colors.electric} side={DoubleSide} />
        </mesh>
      );
    case 'MEMORY_DUMP':
      return (
        <mesh>
          <cylinderGeometry args={[0.06, 0.06, 0.14, 6]} />
          <meshStandardMaterial color={colors.graphite} wireframe />
        </mesh>
      );
    case 'REPORT':
      return (
        <mesh rotation={[0.1, 0.2, 0.3]}>
          <boxGeometry args={[0.1, 0.14, 0.02]} />
          <meshStandardMaterial color={colors.mint} />
        </mesh>
      );
    case 'HTTP_REQUEST':
    case 'HTTP_RESPONSE':
      return (
        <mesh rotation={[0.4, 0.6, 0.1]}>
          <coneGeometry args={[0.06, 0.12, 4]} />
          <meshStandardMaterial color={colors.electric} />
        </mesh>
      );
    case 'LOG':
      return (
        <mesh rotation={[0.3, 0.5, 0.2]}>
          <boxGeometry args={[0.08, 0.1, 0.04]} />
          <meshStandardMaterial color={colors.link} />
        </mesh>
      );
    case 'FILE':
      return (
        <mesh rotation={[0.3, 0.5, 0.2]}>
          <boxGeometry args={[0.09, 0.11, 0.05]} />
          <meshStandardMaterial color={colors.amber} />
        </mesh>
      );
    default:
      return (
        <mesh rotation={[0.3, 0.5, 0.2]}>
          <octahedronGeometry args={[0.08, 0]} />
          <meshStandardMaterial color={colors.mint} />
        </mesh>
      );
  }
}

export function EvidenceArtifact({
  artifactType,
  position = [0, 0, 0],
  selected,
  onClick,
}: EvidenceArtifactProps) {
  return (
    <group
      position={position}
      onClick={(e) => {
        e.stopPropagation();
        onClick?.();
      }}
    >
      <ArtifactGeometry type={artifactType} />
      {selected && (
        <mesh scale={1.4}>
          <octahedronGeometry args={[0.09, 0]} />
          <meshBasicMaterial color={colors.selection} wireframe transparent opacity={0.4} />
        </mesh>
      )}
    </group>
  );
}
