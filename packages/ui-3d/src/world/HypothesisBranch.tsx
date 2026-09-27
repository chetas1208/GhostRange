import { colors } from '../materials/theme';
import { WorldFork } from './WorldFork';

export type HypothesisBranchProps = {
  from: [number, number, number];
  to: [number, number, number];
  /** 0–1 fill from backend fork / provisioning progress */
  progress?: number;
  active?: boolean;
};

/** Multiverse remediation branch connector (§8.5). */
export function HypothesisBranch({ from, to, progress = 0.35, active = true }: HypothesisBranchProps) {
  if (!active) return null;

  const mid: [number, number, number] = [
    (from[0] + to[0]) / 2,
    Math.max(from[1], to[1]) + 0.4,
    (from[2] + to[2]) / 2,
  ];

  return (
    <group>
      <WorldFork from={from} to={to} progress={progress} fill={progress} />
      <line>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={3}
            array={new Float32Array([...from, ...mid, ...to])}
            itemSize={3}
          />
        </bufferGeometry>
        <lineBasicMaterial color={colors.link} transparent opacity={0.25 + progress * 0.35} />
      </line>
    </group>
  );
}
