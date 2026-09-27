import { describe, expect, it } from 'vitest';
import { chunkVec3 } from '../ui/canvas/cameraFraming';
import { createInitialState } from './eventReducer';
import {
  selectEvidenceNodePositions,
  selectExecutionNodePositions,
  selectMultiverseNodePositions,
} from './selectors';
import type { ArtifactV1, ClaimV1, ComputeWorkerV1, WorldV1 } from './types';

function world(overrides: Partial<WorldV1> & { id: string }): WorldV1 {
  return {
    range_id: 'r1',
    label: overrides.id,
    status: 'READY',
    ...overrides,
  };
}

function worker(overrides: Partial<ComputeWorkerV1> & { id: string }): ComputeWorkerV1 {
  return {
    resource_class: 'CPU_SMALL',
    status: 'READY',
    region: 'ewr',
    cost_per_hour_usd: 0.01,
    ...overrides,
  };
}

describe('selectMultiverseNodePositions', () => {
  it('is empty when there are no worlds (the true zero-node state)', () => {
    const state = createInitialState();
    expect(selectMultiverseNodePositions(state)).toEqual([]);
  });

  it('returns exactly one position for a single root world (the realistic sparse case)', () => {
    const state = createInitialState();
    state.worlds = { w1: world({ id: 'w1' }) };
    const positions = selectMultiverseNodePositions(state);
    expect(chunkVec3(positions)).toHaveLength(1);
  });

  it('includes forked children alongside the root, one position per world', () => {
    const state = createInitialState();
    state.worlds = {
      w1: world({ id: 'w1' }),
      w2: world({ id: 'w2', parent_world_id: 'w1' }),
      w3: world({ id: 'w3', parent_world_id: 'w1' }),
    };
    const positions = selectMultiverseNodePositions(state);
    expect(chunkVec3(positions)).toHaveLength(3);
  });

  it('excludes destroyed worlds but keeps ones still mid-DESTROYING', () => {
    const state = createInitialState();
    state.worlds = {
      w1: world({ id: 'w1', destroyed: true, status: 'DESTROYED' }),
      w2: world({ id: 'w2', destroyed: true, status: 'DESTROYING' }),
    };
    const positions = selectMultiverseNodePositions(state);
    expect(chunkVec3(positions)).toHaveLength(1);
  });

  it('returns a flat, primitive number[] (shallow-comparable — see the selector\'s doc comment)', () => {
    const state = createInitialState();
    state.worlds = { w1: world({ id: 'w1' }) };
    const positions = selectMultiverseNodePositions(state);
    expect(positions.every((n) => typeof n === 'number')).toBe(true);
    expect(positions).toEqual([0, 0.15, 0]);
  });
});

describe('selectExecutionNodePositions', () => {
  it('is empty with no workers or tasks', () => {
    const state = createInitialState();
    expect(selectExecutionNodePositions(state)).toEqual([]);
  });

  it('counts one live worker plus its tasks (the realistic "1 real worker" case)', () => {
    const state = createInitialState();
    state.workers = { cw1: worker({ id: 'cw1' }) };
    state.tasks = {
      t1: { id: 't1', world_id: 'w1', task_type: 'health', dependencies: [], status: 'RUNNING' },
    };
    const positions = selectExecutionNodePositions(state);
    expect(chunkVec3(positions)).toHaveLength(2);
  });

  it('excludes released workers', () => {
    const state = createInitialState();
    state.workers = {
      cw1: worker({ id: 'cw1', status: 'RELEASED' }),
      cw2: worker({ id: 'cw2', status: 'READY' }),
    };
    const positions = selectExecutionNodePositions(state);
    expect(chunkVec3(positions)).toHaveLength(1);
  });

  it('applies ExecutionScene\'s -8 z offset so camera framing matches what is actually rendered', () => {
    const state = createInitialState();
    state.workers = { cw1: worker({ id: 'cw1', slot: 0 }) };
    const [pos] = chunkVec3(selectExecutionNodePositions(state));
    expect(pos[2]).toBe(-8);
  });
});

describe('selectEvidenceNodePositions', () => {
  it('is empty with no claim or artifacts', () => {
    const state = createInitialState();
    expect(selectEvidenceNodePositions(state)).toEqual([]);
  });

  it('counts the primary claim plus each artifact', () => {
    const state = createInitialState();
    const claim: ClaimV1 = { id: 'c1', world_id: 'w1', statement: 'x', anchored: true, verified: false };
    const artifact: ArtifactV1 = { id: 'a1', world_id: 'w1', artifact_type: 'LOG', content_hash: 'h' };
    state.claims = { c1: claim };
    state.artifacts = { a1: artifact };
    const positions = selectEvidenceNodePositions(state);
    expect(chunkVec3(positions)).toHaveLength(2);
  });

  it("applies EvidenceScene's -15 z offset so camera framing matches what is actually rendered", () => {
    const state = createInitialState();
    state.claims = { c1: { id: 'c1', world_id: 'w1', statement: 'x', anchored: true, verified: false } };
    const [pos] = chunkVec3(selectEvidenceNodePositions(state));
    expect(pos[2]).toBe(-15);
  });
});
