import type { GhostEvent } from './types';

/** Backend flat event (packages/events) or API envelope → reducer input. */
export function normalizeEnvelope(raw: Record<string, unknown>, sequence = 0): GhostEvent {
  const eventName = (raw.event_name ?? raw.type) as string;
  const id = String(raw.event_id ?? raw.id ?? crypto.randomUUID());
  const occurred_at = String(raw.occurred_at ?? new Date().toISOString());

  return {
    id,
    sequence: Number(raw.sequence ?? sequence),
    type: eventName,
    occurred_at,
    payload: raw,
  };
}

export function eventLogLabel(type: string, payload: Record<string, unknown>): string {
  switch (type) {
    case 'world.requested':
      return 'World requested';
    case 'world.provisioning':
      return 'World provisioning';
    case 'world.ready':
      return 'World ready';
    case 'world.destroyed':
      return 'World destroyed';
    case 'compute.requested':
      return 'Compute requested';
    case 'compute.provisioning':
      return 'Compute provisioning';
    case 'compute.ready':
      return 'Compute ready';
    case 'compute.released':
      return 'Compute released';
    case 'task.started':
      return `Task started ${String(payload.task_id ?? '').slice(0, 8)}`;
    case 'verification.passed':
      return 'Verification passed';
    case 'evidence.created':
      return 'Evidence created';
    case 'cost.snapshot.updated':
      return `Cost ${String(payload.display_known_total ?? payload.semantic_type ?? 'updated')}`;
    case 'golden_path.phase':
      return `Golden path: ${String(payload.phase ?? '')}`;
    case 'director.decision':
      return 'GhostDirector decision';
    case 'scheduler.plan':
      return 'GhostScheduler plan';
    case 'ghostledger.sealed':
      return 'Experiment sealed';
    case 'promotion.created':
      return 'GhostGate: promotion package created';
    case 'approval.requested':
      return 'Approval requested (human review)';
    case 'rollback.test_passed':
      return 'Rollback drill passed in range';
    case 'rollback.test_failed':
      return 'Rollback drill failed in range';
    case 'deployment.observed':
      return 'Deployment observed (GhostWatch)';
    case 'rollout.hold':
      return 'Rollout hold';
    case 'rollout.rollback_recommended':
      return 'Rollback recommended';
    case 'production.surprise_detected':
      return 'Production surprise detected';
    case 'world.fork.created':
      return `Fork ${String(payload.branch_label ?? '')}`;
    case 'mesh.contribution_published':
      return 'Mesh contribution published';
    case 'mesh.contribution_received':
      return 'Mesh contribution received';
    case 'mesh.contribution_quarantined':
      return 'Mesh contribution quarantined';
    case 'mesh.contribution_revoked':
      return 'Mesh contribution revoked';
    case 'mesh.prior_used':
      return 'Mesh prior influenced Director';
    case 'mesh.local_validation_passed':
      return 'Mesh prior locally supported';
    case 'mesh.local_validation_failed':
      return 'Mesh prior locally rejected';
    case 'mesh.negative_transfer_detected':
      return 'Mesh negative transfer';
    case 'causal.intervention_completed':
      return 'Causal intervention completed';
    case 'causal.edge_supported':
      return 'Causal edge intervention-supported';
    case 'causal.transport_rejected':
      return 'Causal transport rejected';
    default:
      return type;
  }
}
