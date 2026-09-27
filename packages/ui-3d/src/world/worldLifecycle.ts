import type { SemanticState } from '../materials/theme';
import type { WorldLifecycleStatus } from '../types';

export function worldLifecycleToSemantic(status: WorldLifecycleStatus): SemanticState {
  switch (status) {
    case 'REQUESTED':
      return 'healthy';
    case 'PROVISIONING':
    case 'BOOTING':
      return 'provisioning';
    case 'EXECUTING':
      return 'investigating';
    case 'VERIFYING':
      return 'verifying';
    case 'VERIFIED':
      return 'verified';
    case 'FAILED':
      return 'failed';
    case 'PRUNED':
    case 'DESTROYING':
    case 'DESTROYED':
      return 'pruned';
    default:
      return 'healthy';
  }
}
