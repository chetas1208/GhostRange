import type { AgentType } from '../types';
import { AdversaryProbe } from './AdversaryProbe';
import { DefenderProbe } from './DefenderProbe';
import { InvestigatorProbe } from './InvestigatorProbe';
import { VerifierProbe } from './VerifierProbe';

export type AgentEntityProps = {
  agentType: AgentType;
  position?: [number, number, number];
};

export function AgentEntity({ agentType, position }: AgentEntityProps) {
  switch (agentType) {
    case 'ADVERSARY':
      return <AdversaryProbe position={position} />;
    case 'VERIFIER':
      return <VerifierProbe position={position} />;
    case 'REMEDIATOR':
      return <DefenderProbe position={position} />;
    default:
      return <InvestigatorProbe position={position} />;
  }
}
