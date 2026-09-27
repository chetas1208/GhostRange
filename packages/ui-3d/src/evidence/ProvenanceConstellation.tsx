import type { ReactNode } from 'react';
import { ClaimNode } from './ClaimNode';
import { EvidenceLink } from './EvidenceLink';

export type ConstellationBranch = {
  id: string;
  label: string;
  position: [number, number, number];
  children?: ConstellationBranch[];
};

export type ProvenanceConstellationProps = {
  claimPosition?: [number, number, number];
  claimAnchored?: boolean;
  claimVerified?: boolean;
  branches: ConstellationBranch[];
  onClaimClick?: () => void;
  onArtifactClick?: (id: string) => void;
  children?: ReactNode;
};

export function ProvenanceConstellation({
  claimPosition = [0, 0.5, 0],
  claimAnchored,
  claimVerified,
  branches,
  onClaimClick,
}: ProvenanceConstellationProps) {
  return (
    <group>
      <group position={claimPosition}>
        <ClaimNode anchored={claimAnchored} verified={claimVerified} onClick={onClaimClick} />
      </group>
      {branches.map((b) => (
        <group key={b.id}>
          <EvidenceLink from={claimPosition} to={b.position} anchored={claimAnchored ?? false} />
          <mesh position={b.position}>
            <sphereGeometry args={[0.06, 8, 8]} />
            <meshStandardMaterial color="#6ee7b7" />
          </mesh>
          {b.children?.map((c) => (
            <EvidenceLink key={c.id} from={b.position} to={c.position} anchored={claimAnchored ?? false} />
          ))}
        </group>
      ))}
    </group>
  );
}
