import { eventLogLabel } from './normalizeEnvelope';
import type {
  ArtifactV1,
  AssetV1,
  ClaimV1,
  ComputeWorkerV1,
  GhostEvent,
  GhostState,
  NetworkLinkV1,
  ProviderKind,
  RangeV1,
  SchedulerDecisionV1,
  TaskV1,
  WorldForkV1,
  WorldV1,
} from './types';

export function createInitialState(): GhostState {
  return {
    range: null,
    campaignId: null,
    campaignPhase: null,
    streamRangeId: null,
    lastEventSeq: 0,
    sseStatus: 'idle',
    arenaQualification: null,
    worlds: {},
    forks: [],
    assets: {},
    links: {},
    workers: {},
    tasks: {},
    decisions: {},
    agents: {},
    artifacts: {},
    claims: {},
    attacks: [],
    processedEventIds: new Set(),
    liveEventBuffer: [],
    releasedWorkerIds: new Set(),
    sequence: 0,
    totalCostUsd: 0,
    costRevision: 0,
    costSemanticType: null,
    costUnknownComponents: [],
    taskTiming: {},
    live: true,
    mode: 'multiverse',
    cameraLevel: 'multiverse',
    focusedWorldId: null,
    selection: null,
    replayTimeMs: 0,
    replayMaxMs: 90_000,
    timelineMarkers: [],
    dataSource: 'fixture',
    streamConnected: false,
    activeProvider: null,
    eventLog: [],
    ariaSelectionSummary: '',
    replayScrubbing: false,
    hoverTarget: null,
    streamError: null,
    verificationRing: 'pending',
    cameraDolly: 0,
    promotion: null,
    ghostwatch: null,
    mesh: null,
    causal: null,
    authorizationGate: null,
  };
}

function appendLog(next: GhostState, event: GhostEvent) {
  next.eventLog = [
    ...next.eventLog,
    {
      id: event.id,
      type: event.type,
      occurred_at: event.occurred_at,
      label: eventLogLabel(event.type, event.payload),
    },
  ].slice(-200);
}

function mapProvider(p: unknown): ProviderKind {
  if (p === 'VULTR' || p === 'vultr') return 'vultr';
  if (p === 'LOCAL_MOCK' || p === 'mock') return 'mock';
  return null;
}

function upsertWorld(state: GhostState, world: WorldV1) {
  const prev = state.worlds[world.id];
  state.worlds[world.id] = {
    ...prev,
    ...world,
    fill: world.fill ?? prev?.fill ?? (world.status === 'PROVISIONING' ? 0.2 : 1),
  };
}

export function reduceEvent(state: GhostState, event: GhostEvent): GhostState {
  if (state.processedEventIds.has(event.id)) return state;
  const next: GhostState = {
    ...state,
    worlds: { ...state.worlds },
    assets: { ...state.assets },
    links: { ...state.links },
    workers: { ...state.workers },
    tasks: { ...state.tasks },
    decisions: { ...state.decisions },
    agents: { ...state.agents },
    artifacts: { ...state.artifacts },
    claims: { ...state.claims },
    attacks: [...state.attacks],
    forks: [...state.forks],
    processedEventIds: new Set(state.processedEventIds),
    releasedWorkerIds: new Set(state.releasedWorkerIds),
    timelineMarkers: [...state.timelineMarkers],
  };
  next.processedEventIds.add(event.id);
  next.sequence = Math.max(next.sequence, event.sequence);
  appendLog(next, event);

  const p = event.payload;

  switch (event.type) {
    case 'range.updated': {
      const range = p.range as RangeV1 | undefined;
      if (range?.id) next.range = range;
      break;
    }
    case 'world.created':
      upsertWorld(next, p.world as WorldV1);
      break;
    case 'world.status_changed': {
      const id = p.world_id as string;
      const w = next.worlds[id];
      if (w) {
        const status = p.status as WorldV1['status'];
        let fill = w.fill ?? 1;
        if (status === 'PROVISIONING') fill = Math.max(fill, 0.35);
        if (status === 'READY' || status === 'EXECUTING') fill = 1;
        next.worlds[id] = { ...w, status, failure_reason: (p.failure_reason as string) ?? w.failure_reason, fill };
      }
      break;
    }
    case 'world.forked': {
      const fork = p.fork as WorldForkV1;
      const child = p.child as WorldV1;
      next.forks.push(fork);
      const provisioning =
        child.status === 'PROVISIONING' || child.status === 'BOOTING' || child.status === 'REQUESTED';
      upsertWorld(next, {
        ...child,
        fill: provisioning ? 0.15 : (child.fill ?? 1),
        shell_visible: provisioning || child.shell_visible,
        network_ready: child.status === 'READY' || child.network_ready,
      });
      for (const asset of Object.values(next.assets)) {
        if (asset.world_id === fork.parent_world_id) {
          const clone: AssetV1 = {
            ...asset,
            id: `${asset.id}-${child.id}`,
            world_id: child.id,
          };
          next.assets[clone.id] = clone;
        }
      }
      for (const link of Object.values(next.links)) {
        if (link.world_id === fork.parent_world_id) {
          const clone: NetworkLinkV1 = {
            ...link,
            id: `${link.id}-${child.id}`,
            world_id: child.id,
            from_id: `${link.from_id}-${child.id}`,
            to_id: `${link.to_id}-${child.id}`,
          };
          next.links[clone.id] = clone;
        }
      }
      break;
    }
    case 'world.collapsed': {
      const id = p.world_id as string;
      const w = next.worlds[id];
      if (w) next.worlds[id] = { ...w, collapsed: true, status: 'FAILED', failure_reason: p.reason as string };
      break;
    }
    case 'asset.upserted':
      next.assets[(p.asset as AssetV1).id] = p.asset as AssetV1;
      break;
    case 'link.upserted':
      next.links[(p.link as NetworkLinkV1).id] = p.link as NetworkLinkV1;
      break;
    case 'attack.observed':
      next.attacks.push({
        world_id: p.world_id as string,
        path_asset_ids: p.path as string[],
        active: true,
      });
      break;
    case 'attack.outcome': {
      const target = p.target_asset_id as string;
      if (next.assets[target]) next.assets[target] = { ...next.assets[target], fractured: true };
      next.attacks = next.attacks.map((a) =>
        a.world_id === p.world_id ? { ...a, active: false } : a,
      );
      break;
    }
    case 'compute.worker_upserted':
      next.workers[(p.worker as ComputeWorkerV1).id] = p.worker as ComputeWorkerV1;
      break;
    case 'compute.worker_status_changed': {
      const id = p.worker_id as string;
      const w = next.workers[id];
      if (w) {
        const status = p.status as ComputeWorkerV1['status'];
        next.workers[id] = { ...w, status };
        // Authoritative cost: cost.snapshot.updated / compute.released — not client-side proration.
        const slot = w.slot ?? 0;
        const pos: [number, number, number] = [-3 + slot * 1.4, 0.6, -8];
        if (status === 'REQUESTED' || status === 'PROVISIONING') {
          next.authorizationGate = {
            position: pos,
            state: 'EVALUATING',
            actionType: 'CREATE_WORKER',
          };
        } else if (status === 'READY' || status === 'BUSY') {
          next.authorizationGate = {
            position: pos,
            state: 'AUTHORIZED',
            actionType: 'CREATE_WORKER',
          };
        } else if (status === 'FAILED') {
          next.authorizationGate = {
            position: pos,
            state: 'DENIED',
            actionType: 'CREATE_WORKER',
            reason: 'Worker failed',
          };
        }
      }
      break;
    }
    case 'task.upserted':
      next.tasks[(p.task as TaskV1).id] = p.task as TaskV1;
      break;
    case 'task.status_changed': {
      const id = p.task_id as string;
      const t = next.tasks[id];
      if (t) next.tasks[id] = { ...t, status: p.status as TaskV1['status'] };
      break;
    }
    case 'scheduler.decision': {
      const d = (p.decision ?? p) as SchedulerDecisionV1;
      if (d.id && d.task_id) next.decisions[d.id] = d;
      break;
    }
    case 'agent.upserted':
      next.agents[(p.agent as { id: string }).id] = p.agent as GhostState['agents'][string];
      break;
    case 'evidence.artifact_created':
      next.artifacts[(p.artifact as ArtifactV1).id] = {
        ...(p.artifact as ArtifactV1),
        ...(p.detail as object),
      };
      break;
    case 'evidence.claim_updated':
      next.claims[(p.claim as ClaimV1).id] = p.claim as ClaimV1;
      break;
    case 'evidence.verification_completed': {
      const claimId = p.claim_id as string;
      const c = next.claims[claimId];
      if (c) next.claims[claimId] = { ...c, verified: true, anchored: true };
      break;
    }
    case 'timeline.marker':
      next.timelineMarkers.push({ t: p.t as number, label: p.label as string });
      break;
    case 'cost.tick':
      next.totalCostUsd += (p.delta_usd as number) ?? 0;
      break;
    case 'cost.snapshot.updated': {
      const micros = Number(p.total_known_usd_micros ?? 0);
      next.totalCostUsd = micros / 1_000_000;
      next.costSemanticType = String(p.semantic_type ?? 'ACCRUED_ESTIMATE');
      next.costUnknownComponents = Array.isArray(p.unknown_components)
        ? (p.unknown_components as string[])
        : [];
      next.costRevision += 1;
      break;
    }

    /* —— M2 canonical events (packages/events) —— */
    case 'world.requested': {
      const worldId = String(p.world_id);
      upsertWorld(next, {
        id: worldId,
        range_id: String(p.range_id),
        parent_world_id: p.parent_world_id ? String(p.parent_world_id) : null,
        label: 'ghostrange-auth-lab-v1',
        status: 'REQUESTED',
        shell_visible: false,
        network_ready: false,
        fill: 0,
      });
      break;
    }
    case 'world.provisioning': {
      const worldId = String(p.world_id);
      upsertWorld(next, {
        id: worldId,
        range_id: String(p.range_id),
        label: next.worlds[worldId]?.label ?? 'World',
        status: 'PROVISIONING',
        shell_visible: true,
        network_ready: false,
        fill: 0.2,
      });
      break;
    }
    case 'world.booting': {
      const worldId = String(p.world_id);
      const prev = next.worlds[worldId];
      if (prev) {
        next.worlds[worldId] = {
          ...prev,
          status: 'PROVISIONING',
          shell_visible: true,
          network_ready: false,
          fill: Math.max(prev.fill ?? 0, 0.5),
        };
      }
      break;
    }
    case 'world.ready': {
      const worldId = String(p.world_id);
      const prev = next.worlds[worldId];
      upsertWorld(next, {
        ...(prev ?? {
          id: worldId,
          range_id: String(p.range_id),
          label: 'ghostrange-auth-lab-v1',
        }),
        status: 'READY',
        shell_visible: true,
        network_ready: true,
        fill: 1,
      });
      break;
    }
    case 'world.executing': {
      const worldId = String(p.world_id);
      const w = next.worlds[worldId];
      if (w) next.worlds[worldId] = { ...w, status: 'EXECUTING' };
      break;
    }
    case 'world.verifying': {
      const worldId = String(p.world_id);
      const w = next.worlds[worldId];
      if (w) next.worlds[worldId] = { ...w, status: 'VERIFYING' };
      break;
    }
    case 'world.destroying': {
      const worldId = String(p.world_id);
      const w = next.worlds[worldId];
      if (w) {
        next.worlds[worldId] = {
          ...w,
          status: 'DESTROYING',
          network_ready: true,
        };
      }
      break;
    }
    case 'world.destroyed': {
      const worldId = String(p.world_id);
      const w = next.worlds[worldId];
      if (w) {
        next.worlds[worldId] = {
          ...w,
          destroyed: true,
          shell_visible: false,
          network_ready: false,
          status: 'DESTROYED',
        };
      }
      break;
    }
    case 'compute.requested': {
      const id = String(p.compute_worker_id);
      next.workers[id] = {
        id,
        resource_class: p.resource_class as ComputeWorkerV1['resource_class'],
        status: 'REQUESTED',
        region: String(p.region ?? 'ewr'),
        cost_per_hour_usd: 0,
        world_id: p.world_id ? String(p.world_id) : null,
        materialized: false,
        provider: mapProvider(p.provider),
      };
      break;
    }
    case 'compute.provisioning': {
      const id = String(p.compute_worker_id);
      const prev = next.workers[id];
      const provider = mapProvider(p.provider);
      if (provider) next.activeProvider = provider;
      next.workers[id] = {
        ...(prev ?? {
          id,
          resource_class: 'CPU_MEDIUM',
          region: String(p.region ?? 'ewr'),
          cost_per_hour_usd: 0,
        }),
        status: 'PROVISIONING',
        materialized: false,
        provider: provider ?? prev?.provider,
      };
      break;
    }
    case 'compute.booting': {
      const id = String(p.compute_worker_id);
      if (next.workers[id]) next.workers[id] = { ...next.workers[id], status: 'BOOTING' };
      break;
    }
    case 'compute.ready': {
      const id = String(p.compute_worker_id);
      if (next.releasedWorkerIds.has(id)) break;
      const prev = next.workers[id];
      if (prev?.status === 'RELEASED' || prev?.status === 'DESTROYING') break;
      const provider = mapProvider(p.provider);
      if (provider) next.activeProvider = provider;
      next.workers[id] = {
        id,
        resource_class: p.resource_class as ComputeWorkerV1['resource_class'],
        status: 'READY',
        region: String(p.region),
        cost_per_hour_usd: Number(p.cost_per_hour_usd ?? 0),
        world_id: p.world_id ? String(p.world_id) : null,
        provider_instance_id: String(p.provider_instance_id ?? ''),
        provider: provider ?? 'mock',
        materialized: true,
        utilization: 0.2,
      };
      break;
    }
    case 'compute.busy': {
      const id = String(p.compute_worker_id);
      if (next.workers[id]) {
        next.workers[id] = { ...next.workers[id], status: 'BUSY', utilization: 0.7 };
      }
      break;
    }
    case 'compute.draining':
    case 'compute.destroying': {
      const id = String(p.compute_worker_id);
      if (next.workers[id]) {
        next.workers[id] = {
          ...next.workers[id],
          status: event.type === 'compute.draining' ? 'DRAINING' : 'DESTROYING',
        };
      }
      break;
    }
    case 'compute.released': {
      const id = String(p.compute_worker_id);
      next.releasedWorkerIds.add(id);
      delete next.workers[id];
      next.totalCostUsd += Number(p.total_cost_usd ?? 0);
      break;
    }
    case 'task.queued': {
      const id = String(p.task_id);
      next.taskTiming[id] = { ...next.taskTiming[id], queued_at: event.occurred_at };
      const m2Meta: Record<string, { label: string; layout: { x: number; y: number; z: number } }> = {
        't-provision': { label: 'Provision Range', layout: { x: 0, y: 0.5, z: 0 } },
        't-health': { label: 'Health Check', layout: { x: 1.2, y: 0.5, z: 0 } },
        't-validate': { label: 'Validate Condition', layout: { x: 2.4, y: 0.5, z: 0 } },
        't-evidence': { label: 'Collect Evidence', layout: { x: 3.6, y: 0.5, z: 0 } },
        't-verify': { label: 'Verify', layout: { x: 4.8, y: 0.5, z: 0 } },
        't-teardown': { label: 'Teardown', layout: { x: 6, y: 0.5, z: 0 } },
      };
      const meta = m2Meta[id];
      next.tasks[id] = {
        id,
        world_id: String(p.world_id),
        task_type: String(p.task_type),
        dependencies: next.tasks[id]?.dependencies ?? [],
        status: 'QUEUED',
        priority: Number(p.priority ?? 50),
        label: meta?.label ?? next.tasks[id]?.label,
        layout: meta?.layout ?? next.tasks[id]?.layout,
      };
      break;
    }
    case 'task.scheduled': {
      const id = String(p.task_id);
      const t = next.tasks[id];
      if (t) next.tasks[id] = { ...t, status: 'SCHEDULED' };
      break;
    }
    case 'task.started': {
      const id = String(p.task_id);
      next.taskTiming[id] = { ...next.taskTiming[id], started_at: event.occurred_at };
      const t = next.tasks[id];
      if (t) next.tasks[id] = { ...t, status: 'RUNNING' };
      const wId = p.compute_worker_id ? String(p.compute_worker_id) : null;
      if (wId && next.workers[wId]) {
        next.workers[wId] = { ...next.workers[wId], status: 'BUSY', utilization: 0.65 };
      }
      break;
    }
    case 'task.completed': {
      const id = String(p.task_id);
      next.taskTiming[id] = { ...next.taskTiming[id], completed_at: event.occurred_at };
      const t = next.tasks[id];
      if (t) next.tasks[id] = { ...t, status: 'COMPLETED' };
      next.totalCostUsd += Number(p.actual_cost_usd ?? 0);
      break;
    }
    case 'task.failed': {
      const id = String(p.task_id);
      next.taskTiming[id] = { ...next.taskTiming[id], failed_at: event.occurred_at };
      const t = next.tasks[id];
      if (t) next.tasks[id] = { ...t, status: 'FAILED' };
      break;
    }
    case 'verification.started': {
      const claimId = String(p.claim_id);
      const c = next.claims[claimId];
      if (c) next.claims[claimId] = { ...c, anchored: false, verified: false };
      next.verificationRing = 'running';
      const worldId = p.world_id ? String(p.world_id) : c?.world_id;
      if (worldId && next.worlds[worldId]) {
        next.worlds[worldId] = { ...next.worlds[worldId], status: 'VERIFYING' };
      }
      break;
    }
    case 'verification.passed': {
      const claimId = String(p.claim_id);
      const c = next.claims[claimId];
      if (c) next.claims[claimId] = { ...c, verified: true, anchored: true };
      next.verificationRing = 'passed';
      const worldId = p.world_id ? String(p.world_id) : c?.world_id;
      if (worldId && next.worlds[worldId]) {
        next.worlds[worldId] = { ...next.worlds[worldId], status: 'VERIFIED' };
      }
      break;
    }
    case 'verification.failed': {
      const claimId = String(p.claim_id);
      const c = next.claims[claimId];
      if (c) next.claims[claimId] = { ...c, verified: false, anchored: false };
      next.verificationRing = 'failed';
      break;
    }
    case 'evidence.created':
      next.timelineMarkers.push({
        t: next.eventLog.length * 1000,
        label: 'evidence',
      });
      break;
    case 'promotion.created':
    case 'promotion.equivalence_checked':
    case 'promotion.risk_assessed':
    case 'approval.requested':
    case 'rollback.test_passed':
    case 'rollback.test_failed': {
      const cid = p.candidate_id ? String(p.candidate_id) : next.promotion?.candidateId;
      if (cid) {
        next.promotion = {
          candidateId: cid,
          state: String(p.state ?? next.promotion?.state ?? 'ASSESSING'),
          hash: String(p.change_candidate_hash ?? next.promotion?.hash ?? ''),
          blockers: next.promotion?.blockers ?? [],
          evidenceRoot: next.promotion?.evidenceRoot ?? '',
          patchPreview: next.promotion?.patchPreview ?? '',
          showProductionShadow: true,
        };
      }
      break;
    }
    case 'mesh.prior_used':
    case 'mesh.local_validation_passed':
    case 'mesh.local_validation_failed': {
      next.mesh = {
        label: String(p.label ?? 'SIMULATED_MESH'),
        bStatus: String(p.status ?? next.mesh?.bStatus ?? ''),
        cStatus: next.mesh?.cStatus ?? '',
        eQuarantined: next.mesh?.eQuarantined ?? false,
        bFirstExperiment: String(p.first_experiment ?? next.mesh?.bFirstExperiment ?? ''),
      };
      break;
    }
    case 'mesh.contribution_quarantined':
      if (next.mesh) next.mesh = { ...next.mesh, eQuarantined: true };
      break;

    case 'causal.intervention_completed':
    case 'causal.edge_supported':
      next.causal = {
        label: String(p.label ?? 'session_refresh_cache'),
        cacheBlocks: Boolean(p.cache_blocks ?? true),
        transportC: String(p.transport ?? p.support ?? 'intervention-supported'),
        rejectsCTransport: next.causal?.rejectsCTransport ?? false,
      };
      break;
    case 'causal.transport_rejected':
      next.causal = {
        label: next.causal?.label ?? 'session_refresh_cache',
        cacheBlocks: next.causal?.cacheBlocks ?? true,
        transportC: next.causal?.transportC ?? '',
        rejectsCTransport: true,
      };
      break;

    case 'execution.denied':
      next.authorizationGate = {
        position: [-2, 0.6, -8],
        state: 'DENIED',
        actionType: String(p.action ?? 'CREATE_WORKER'),
        reason: String(p.reason ?? 'policy'),
      };
      break;

    case 'adversarial.counterexample': {
      const claimId = String(p.claim_id ?? '');
      const c = next.claims[claimId];
      if (c) next.claims[claimId] = { ...c, verified: false, anchored: false };
      next.timelineMarkers.push({ t: next.eventLog.length * 1000, label: 'counterexample' });
      break;
    }

    case 'runtime.interruption': {
      const target = Object.keys(next.assets)[0];
      if (target && next.assets[target]) {
        next.assets[target] = { ...next.assets[target], fractured: true };
      }
      break;
    }
    case 'runtime.recovered':
      next.timelineMarkers.push({ t: next.eventLog.length * 1000, label: 'recovery' });
      break;

    case 'golden_path.phase':
      next.timelineMarkers.push({
        t: next.eventLog.length * 1000,
        label: String(p.phase ?? 'golden'),
      });
      break;

    case 'campaign.phase': {
      const phase = String(p.phase ?? '');
      next.campaignPhase = phase;
      if (p.campaign_id) next.campaignId = String(p.campaign_id);
      if (p.arena_recommendation) next.arenaQualification = String(p.arena_recommendation);
      next.timelineMarkers.push({ t: next.eventLog.length * 1000, label: phase });
      if (phase === 'COMPLETED' && p.arena_recommendation === 'QUALIFIED') {
        next.verificationRing = 'passed';
      }
      break;
    }

    case 'director.decision':
      next.timelineMarkers.push({ t: next.eventLog.length * 1000, label: 'hypothesis' });
      break;

    case 'scheduler.plan': {
      const actions = Number(p.scheduler_decisions ?? 1);
      for (let i = 0; i < actions; i++) {
        const id = `sched-decision-${i}-${event.id.slice(0, 8)}`;
        next.decisions[id] = {
          id,
          task_id: Object.keys(next.tasks)[0] ?? 't-validate',
          world_id: Object.keys(next.worlds)[0] ?? 'world-base',
          target_resource_class: 'CPU_MEDIUM',
          priority: 50,
          estimated_cost_usd: 0.02,
          reason_codes: ['CPU_SUFFICIENT'],
          notes: 'GPU startup dominates end-to-end completion',
          cpu_runtime_sec: 18.2,
          gpu_runtime_sec: 4.1,
        };
      }
      break;
    }

    case 'ghostledger.sealed':
      if (p.verified === true || p.verified === 'true') next.verificationRing = 'passed';
      next.timelineMarkers.push({ t: next.eventLog.length * 1000, label: 'verify' });
      break;

    case 'world.fork.created': {
      const childId = String(p.world_id);
      const parentId = String(p.parent_world_id);
      next.forks.push({
        id: `fork-${childId}`,
        parent_world_id: parentId,
        child_world_id: childId,
        fork_reason: String(p.branch_label ?? 'branch'),
      });
      upsertWorld(next, {
        id: childId,
        range_id: String(next.range?.id ?? p.range_id ?? ''),
        parent_world_id: parentId,
        label: String(p.branch_label ?? 'H?'),
        status: 'PROVISIONING',
        shell_visible: true,
        network_ready: false,
        fill: 0.15,
      });
      break;
    }

    default:
      break;
  }

  return next;
}

export function applyEvents(state: GhostState, events: GhostEvent[]): GhostState {
  return events.reduce(reduceEvent, state);
}
