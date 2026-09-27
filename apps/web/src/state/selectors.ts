import type { SemanticState } from '@ghostrange/ui-3d';
import type { ConnectionStatus, GhostState, Id, WorldV1, WorldStatus } from './types';

export function worldToSemantic(status: WorldStatus, collapsed?: boolean): SemanticState {
  if (collapsed) return 'pruned';
  switch (status) {
    case 'PROVISIONING':
    case 'BOOTING':
      return 'provisioning';
    case 'VERIFYING':
      return 'verifying';
    case 'VERIFIED':
      return 'verified';
    case 'FAILED':
      return 'failed';
    case 'EXECUTING':
      return 'investigating';
    case 'READY':
      return 'healthy';
    case 'DESTROYING':
    case 'DESTROYED':
      return 'pruned';
    default:
      return 'healthy';
  }
}

export function selectConnectionStatus(state: GhostState): ConnectionStatus {
  if (state.replayScrubbing && state.replayTimeMs < state.replayMaxMs - 100) {
    return 'REPLAY';
  }
  if (state.dataSource === 'live') {
    return state.streamConnected ? 'LIVE' : 'DISCONNECTED';
  }
  if (state.replayScrubbing) return 'REPLAY';
  return 'FIXTURE';
}

export function selectHasActiveWorld(state: GhostState): boolean {
  for (const id in state.worlds) {
    const w = state.worlds[id];
    if (!w.destroyed && (w.shell_visible || w.network_ready)) return true;
  }
  return false;
}

export function selectAnyWorkerProvisioning(state: GhostState): boolean {
  for (const id in state.workers) {
    if (state.workers[id].status === 'PROVISIONING') return true;
  }
  return false;
}

export function selectAnyWorldVerifying(state: GhostState): boolean {
  for (const id in state.worlds) {
    if (state.worlds[id].status === 'VERIFYING') return true;
  }
  return false;
}

export function selectAnyActiveAttack(state: GhostState): boolean {
  for (let i = 0; i < state.attacks.length; i++) {
    if (state.attacks[i].active) return true;
  }
  return false;
}

export function selectRootWorlds(state: GhostState): WorldV1[] {
  return Object.values(state.worlds).filter((w) => !w.parent_world_id);
}

export function selectChildWorlds(state: GhostState, parentId: Id): WorldV1[] {
  return Object.values(state.worlds).filter((w) => w.parent_world_id === parentId);
}

export function selectWorldAssets(state: GhostState, worldId: Id) {
  return Object.values(state.assets).filter((a) => a.world_id === worldId);
}

export function selectWorldLinks(state: GhostState, worldId: Id) {
  return Object.values(state.links).filter((l) => l.world_id === worldId);
}

export function selectWorkers(state: GhostState) {
  return Object.values(state.workers).sort((a, b) => (a.slot ?? 0) - (b.slot ?? 0));
}

export function selectTasks(state: GhostState) {
  return Object.values(state.tasks);
}

export function selectActiveAttack(state: GhostState, worldId: Id) {
  return state.attacks.find((a) => a.world_id === worldId && a.active);
}

export function selectWorkerCount(state: GhostState): number {
  return Object.values(state.workers).filter((w) => w.status === 'READY' || w.status === 'BUSY').length;
}

/** Workers that may render (requested → released lifecycle). */
export function selectMaterializedWorkers(state: GhostState, worldId?: Id) {
  return Object.values(state.workers).filter((w) => {
    if (worldId && w.world_id !== worldId) return false;
    return w.status !== 'RELEASED';
  });
}

const M2_TASK_ORDER = ['t-provision', 't-health', 't-validate', 't-evidence', 't-verify', 't-teardown'];

export function selectM2ExecutionTasks(state: GhostState) {
  const tasks = Object.values(state.tasks);
  return M2_TASK_ORDER.map((id) => tasks.find((t) => t.id === id)).filter(Boolean) as typeof tasks;
}

export function selectPrimaryClaim(state: GhostState) {
  return Object.values(state.claims)[0] ?? null;
}

export function selectConstellationBranches(state: GhostState) {
  const arts = Object.values(state.artifacts);
  return [
    { id: 'exploit', label: 'Exploit', position: [-1.5, 0, 0.8] as [number, number, number], children: [] },
    { id: 'patch', label: 'Patch', position: [0, 0, 1.2] as [number, number, number], children: [] },
    {
      id: 'retest',
      label: 'Retest',
      position: [1.5, 0, 0.8] as [number, number, number],
      children: arts.slice(0, 3).map((a, i) => ({
        id: a.id,
        label: a.artifact_type,
        position: [1.5 + i * 0.3, -0.4, 0.5 + i * 0.2] as [number, number, number],
      })),
    },
  ];
}

export function selectWorldLayout(
  world: WorldV1,
  index: number,
  siblingCount = 4,
): [number, number, number] {
  if (!world.parent_world_id) return [0, 0.15, 0];
  const count = Math.max(siblingCount, 1);
  const radius = 3.8 + (index % 2) * 0.6;
  const angle = (index / count) * Math.PI * 2 - Math.PI / 2;
  return [Math.cos(angle) * radius, 0.12 + (index % 3) * 0.06, Math.sin(angle) * radius];
}

/** Discrete fork edge progress from world lifecycle (not arbitrary %). */
export function selectForkBranchProgress(world: WorldV1): number {
  if (world.network_ready) return 1;
  if (world.shell_visible) return 0.66;
  if (world.status === 'REQUESTED') return 0.15;
  return 0.33;
}
