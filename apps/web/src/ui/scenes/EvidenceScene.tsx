import {
  EvidenceArtifact,
  EvidenceLink,
  ProvenanceConstellation,
  QualificationGate,
  SealedRange,
  VerificationRing,
} from '@ghostrange/ui-3d';
import { useMemo } from 'react';
import { useGhostStore } from '../../state/store';
import { selectConstellationBranches } from '../../state/selectors';
import type { GhostState } from '../../state/types';

const EMPTY_BRANCHES: ReturnType<typeof selectConstellationBranches> = [];

export function EvidenceScene() {
  const mode = useGhostStore((s) => s.mode);
  const claimsRecord = useGhostStore((s) => s.claims);
  const artifactsRecord = useGhostStore((s) => s.artifacts);
  const claim = useMemo(() => Object.values(claimsRecord)[0] ?? null, [claimsRecord]);
  const branches = useMemo(() => {
    if (mode !== 'evidence') return EMPTY_BRANCHES;
    return selectConstellationBranches({ artifacts: artifactsRecord } as GhostState);
  }, [mode, artifactsRecord]);
  const artifacts = useMemo(
    () => (mode === 'evidence' ? Object.values(artifactsRecord) : []),
    [mode, artifactsRecord],
  );
  const selection = useGhostStore((s) => s.selection);
  const setSelection = useGhostStore((s) => s.setSelection);
  const ringState = useGhostStore((s) => s.verificationRing);
  const focusId = selection?.kind === 'artifact' ? selection.id : null;

  if (mode !== 'evidence') return null;

  return (
    <group position={[0, 0, -15]}>
      <SealedRange scenarioFamily="HIDDEN_GENERALIZATION" sealed={ringState !== 'passed'} />
      <QualificationGate
        recommendation={ringState === 'passed' ? 'QUALIFIED' : 'INSUFFICIENT_EVIDENCE'}
      />
      <ProvenanceConstellation
        claimAnchored={claim?.anchored}
        claimVerified={claim?.verified}
        branches={branches}
        onClaimClick={() => claim && setSelection({ kind: 'claim', id: claim.id })}
      />
      <group position={[0, 0.55, 0]}>
        <VerificationRing state={ringState} />
      </group>
      {claim && artifacts[0] && (
        <EvidenceLink from={[0, 0.5, 0]} to={[artifacts[0].layout?.x ?? 1.2, -0.5, 0.3]} />
      )}
      {artifacts.map((a, i) => {
        const base: [number, number, number] = [
          a.layout?.x ?? 1.2 + i * 0.35,
          a.layout?.y ?? -0.5,
          a.layout?.z ?? 0.3,
        ];
        const pull = focusId && focusId !== a.id ? 0.35 : 1;
        const pos: [number, number, number] = [base[0] * pull, base[1], base[2]];
        return (
          <EvidenceArtifact
            key={a.id}
            artifactType={a.artifact_type}
            position={pos}
            selected={selection?.kind === 'artifact' && selection.id === a.id}
            onClick={() => setSelection({ kind: 'artifact', id: a.id })}
          />
        );
      })}
    </group>
  );
}
