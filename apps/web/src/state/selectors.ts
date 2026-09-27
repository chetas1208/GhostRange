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

// ---------------------------------------------------------------------------
// Camera-fit node positions.
//
// CameraRig fits the overview camera (Multiverse/Execution/Evidence) to the
// real node count/spread instead of a fixed preset distance (see
// ui/canvas/cameraFraming.ts) — that's the mechanism that keeps 1-4 real
// nodes from looking lost in a void sized for a busy demo. These selectors
// mirror each scene's own layout math (MultiverseScene/ExecutionScene/
// EvidenceScene) closely enough to give the camera an accurate bounding
// volume, without importing R3F scene components into the state layer.
//
// They return a **flat `number[]`** (x0,y0,z0, x1,y1,z1, ...) rather than an
// array of `[x,y,z]` tuples deliberately: `useShallow` (and React's
// underlying `useSyncExternalStore`) compares the returned array one level
// deep by reference. An array of freshly-allocated tuple objects is never
// shallow-equal to the previous call's tuples even when every value is
// identical, so the subscription never stabilizes — that starves React's
// snapshot check and throws "Maximum update depth exceeded". A flat array of
// primitives *is* correctly shallow-comparable, so unrelated store updates
// don't force CameraRig to re-render. Callers chunk it back into Vec3s (see
// `chunkVec3` in `ui/canvas/cameraFraming.ts`).
// ---------------------------------------------------------------------------

/** Mirrors ExecutionScene's `<group position={[0, 0, -8]}>` wrapper. */
const EXECUTION_SCENE_OFFSET: [number, number, number] = [0, 0, -8];
/** Mirrors EvidenceScene's `<group position={[0, 0, -15]}>` wrapper. */
const EVIDENCE_SCENE_OFFSET: [number, number, number] = [0, 0, -15];

/** World positions as actually laid out in MultiverseScene (roots + forked children), flattened. */
export function selectMultiverseNodePositions(state: GhostState): number[] {
  const worlds = Object.values(state.worlds).filter((w) => !w.destroyed || w.status === 'DESTROYING');
  const roots = worlds.filter((w) => !w.parent_world_id);
  const children = worlds.filter((w) => w.parent_world_id);

  const positions: number[] = [];
  roots.forEach(() => positions.push(0, 0.15, 0));

  const byParent = new Map<Id, WorldV1[]>();
  for (const child of children) {
    const key = child.parent_world_id as Id;
    const siblings = byParent.get(key) ?? [];
    siblings.push(child);
    byParent.set(key, siblings);
  }
  byParent.forEach((siblings) => {
    siblings.forEach((child, idx) => positions.push(...selectWorldLayout(child, idx, siblings.length)));
  });

  return positions;
}

/** Worker + task positions as actually laid out in ExecutionScene, flattened. */
export function selectExecutionNodePositions(state: GhostState): number[] {
  const workers = selectMaterializedWorkers(state);
  const tasks = selectTasks(state);
  const positions: number[] = [];

  workers.forEach((w) => {
    positions.push(
      -3 + (w.slot ?? 0) * 1.4 + EXECUTION_SCENE_OFFSET[0],
      -1.2 + EXECUTION_SCENE_OFFSET[1],
      EXECUTION_SCENE_OFFSET[2],
    );
  });
  tasks.forEach((t) => {
    positions.push(
      (t.layout?.x ?? 0) + EXECUTION_SCENE_OFFSET[0],
      (t.layout?.y ?? 0.8) + EXECUTION_SCENE_OFFSET[1],
      (t.layout?.z ?? 0) + EXECUTION_SCENE_OFFSET[2],
    );
  });

  return positions;
}

/** Claim + artifact positions as actually laid out in EvidenceScene, flattened. */
export function selectEvidenceNodePositions(state: GhostState): number[] {
  const claim = Object.values(state.claims)[0] ?? null;
  const artifacts = Object.values(state.artifacts);
  const positions: number[] = [];

  if (claim) {
    positions.push(EVIDENCE_SCENE_OFFSET[0], 0.5 + EVIDENCE_SCENE_OFFSET[1], EVIDENCE_SCENE_OFFSET[2]);
  }
  artifacts.forEach((a, i) => {
    positions.push(
      (a.layout?.x ?? 1.2 + i * 0.35) + EVIDENCE_SCENE_OFFSET[0],
      (a.layout?.y ?? -0.5) + EVIDENCE_SCENE_OFFSET[1],
      (a.layout?.z ?? 0.3) + EVIDENCE_SCENE_OFFSET[2],
    );
  });

  return positions;
}
