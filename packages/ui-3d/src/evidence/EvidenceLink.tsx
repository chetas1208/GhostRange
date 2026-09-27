import { colors } from '../materials/theme';

export type EvidenceLinkProps = {
  from: [number, number, number];
  to: [number, number, number];
  anchored?: boolean;
};

export function EvidenceLink({ from, to, anchored = true }: EvidenceLinkProps) {
  return (
    <line>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={2}
          array={new Float32Array([...from, ...to])}
          itemSize={3}
        />
      </bufferGeometry>
      <lineBasicMaterial color={colors.mint} transparent opacity={anchored ? 0.6 : 0.2} />
    </line>
  );
}
