import type { ReactNode } from 'react';

export type SealedRangeProps = {
  scenarioFamily: string;
  sealed: boolean;
  children?: ReactNode;
};

/** Multiverse: evaluation world without hidden verifier details while sealed. */
export function SealedRange({ sealed, children }: SealedRangeProps) {
  return (
    <group name="SealedRange">
      <mesh position={[0, 0.5, 0]}>
        <sphereGeometry args={[1.2, 24, 24]} />
        <meshStandardMaterial color={sealed ? '#1a2a3a' : '#2a4a6a'} transparent opacity={sealed ? 0.85 : 0.5} />
      </mesh>
      {children}
      {/* DOM overlay hook: scenarioFamily shown in parent panel, not ground truth */}
    </group>
  );
}
