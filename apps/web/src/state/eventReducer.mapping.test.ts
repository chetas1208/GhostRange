import { describe, expect, it } from 'vitest';
import { createInitialState, reduceEvent } from './eventReducer';
import type { GhostEvent } from './types';

function ev(type: string, payload: Record<string, unknown>, id = 't1'): GhostEvent {
  return { id, sequence: 1, type, occurred_at: new Date().toISOString(), payload };
}

describe('eventReducer UI truth mapping', () => {
  it('compute.provisioning creates non-materialized worker', () => {
    let s = createInitialState();
    s = reduceEvent(
      s,
      ev('compute.requested', {
        compute_worker_id: 'cw-1',
        resource_class: 'CPU_MEDIUM',
        region: 'ewr',
      }),
    );
    s = reduceEvent(
      s,
      ev('compute.provisioning', { compute_worker_id: 'cw-1', provider: 'LOCAL_MOCK', region: 'ewr' }, 't2'),
    );
    expect(s.workers['cw-1'].status).toBe('PROVISIONING');
    expect(s.workers['cw-1'].materialized).toBeFalsy();
  });

  it('compute.ready materializes worker', () => {
    let s = createInitialState();
    s = reduceEvent(
      s,
      ev('compute.ready', {
        compute_worker_id: 'cw-1',
        resource_class: 'CPU_MEDIUM',
        region: 'ewr',
        provider: 'LOCAL_MOCK',
        provider_instance_id: 'mock-1',
        cost_per_hour_usd: 0.02,
      }),
    );
    expect(s.workers['cw-1'].materialized).toBe(true);
    expect(s.workers['cw-1'].status).toBe('READY');
  });

  it('world.destroying then destroyed hides world from active topology', () => {
    let s = createInitialState();
    s = reduceEvent(s, ev('world.provisioning', { world_id: 'w1', range_id: 'r1' }));
    s = reduceEvent(s, ev('world.ready', { world_id: 'w1', range_id: 'r1' }, 't2'));
    s = reduceEvent(s, ev('world.destroying', { world_id: 'w1', range_id: 'r1' }, 't3'));
    expect(s.worlds.w1.status).toBe('DESTROYING');
    s = reduceEvent(s, ev('world.destroyed', { world_id: 'w1', range_id: 'r1' }, 't4'));
    expect(s.worlds.w1.destroyed).toBe(true);
    expect(s.worlds.w1.shell_visible).toBe(false);
  });

  it('verification.started sets ring running', () => {
    let s = createInitialState();
    s.claims = {
      c1: { id: 'c1', world_id: 'w1', statement: 'test', anchored: false, verified: false },
    };
    s = reduceEvent(s, ev('verification.started', { claim_id: 'c1', world_id: 'w1', verification_id: 'v1' }));
    expect(s.verificationRing).toBe('running');
  });

  it('verification.passed anchors claim', () => {
    let s = createInitialState();
    s.claims = {
      c1: {
        id: 'c1',
        world_id: 'w1',
        statement: 'test',
        anchored: false,
        verified: false,
      },
    };
    s = reduceEvent(s, ev('verification.passed', { claim_id: 'c1', world_id: 'w1', verification_id: 'v1' }));
    expect(s.claims.c1.verified).toBe(true);
    expect(s.claims.c1.anchored).toBe(true);
    expect(s.verificationRing).toBe('passed');
  });

  it('world.forked shows provisioning shell on child worlds', () => {
    let s = createInitialState();
    s = reduceEvent(s, ev('world.ready', { world_id: 'w1', range_id: 'r1' }));
    s = reduceEvent(
      s,
      ev(
        'world.forked',
        {
          fork: { id: 'fk-1', parent_world_id: 'w1', child_world_id: 'w2', fork_reason: 'patch' },
          child: {
            id: 'w2',
            range_id: 'r1',
            parent_world_id: 'w1',
            label: 'Fix A',
            status: 'PROVISIONING',
          },
        },
        't2',
      ),
    );
    expect(s.worlds.w2.shell_visible).toBe(true);
    expect(s.worlds.w2.network_ready).toBeFalsy();
    expect(s.forks).toHaveLength(1);
  });

  it('duplicate event id is idempotent', () => {
    let s = createInitialState();
    const e = ev('world.ready', { world_id: 'w1', range_id: 'r1' }, 'dup-id');
    s = reduceEvent(s, e);
    const s2 = reduceEvent(s, { ...e, sequence: 2 });
    expect(s2).toBe(s);
    expect(Object.keys(s2.worlds)).toHaveLength(Object.keys(s.worlds).length);
  });

  it('compute.ready does not resurrect released worker', () => {
    let s = createInitialState();
    s = reduceEvent(
      s,
      ev('compute.ready', {
        compute_worker_id: 'cw-1',
        resource_class: 'CPU_MEDIUM',
        region: 'ewr',
        provider: 'LOCAL_MOCK',
        provider_instance_id: 'mock-1',
      }),
    );
    s = reduceEvent(s, ev('compute.released', { compute_worker_id: 'cw-1', total_cost_usd: 0.01 }, 'rel'));
    s = reduceEvent(
      s,
      ev(
        'compute.ready',
        {
          compute_worker_id: 'cw-1',
          resource_class: 'CPU_MEDIUM',
          region: 'ewr',
          provider: 'LOCAL_MOCK',
          provider_instance_id: 'mock-late',
        },
        'late',
      ),
    );
    expect(s.workers['cw-1']).toBeUndefined();
  });

  it('scheduler.decision stores decision for inspector', () => {
    let s = createInitialState();
    s = reduceEvent(
      s,
      ev('scheduler.decision', {
        decision: {
          id: 'd-1',
          task_id: 't1',
          world_id: 'w1',
          target_resource_class: 'CPU_MEDIUM',
          priority: 50,
          estimated_cost_usd: 0.02,
          reason_codes: ['CPU_SUFFICIENT'],
        },
      }),
    );
    expect(s.decisions['d-1'].reason_codes).toContain('CPU_SUFFICIENT');
  });
});
