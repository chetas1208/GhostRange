import { describe, expect, it } from 'vitest';
import { chunkVec3, computeBoundingSphere, computeFitDistance, computeFitForPositions } from './cameraFraming';

describe('chunkVec3', () => {
  it('groups a flat number[] into Vec3 triples', () => {
    expect(chunkVec3([1, 2, 3, 4, 5, 6])).toEqual([
      [1, 2, 3],
      [4, 5, 6],
    ]);
  });

  it('is empty for an empty or short input', () => {
    expect(chunkVec3([])).toEqual([]);
    expect(chunkVec3([1, 2])).toEqual([]);
  });
});

describe('computeBoundingSphere', () => {
  it('collapses to a zero-radius sphere at the origin for no positions', () => {
    expect(computeBoundingSphere([])).toEqual({ center: [0, 0, 0], radius: 0 });
  });

  it('is a zero-radius sphere centered on the single position for one node', () => {
    const sphere = computeBoundingSphere([[2, 1, -3]]);
    expect(sphere.center).toEqual([2, 1, -3]);
    expect(sphere.radius).toBeCloseTo(0, 6);
  });

  it('centers on the centroid and radius reaches the farthest point', () => {
    const sphere = computeBoundingSphere([
      [-2, 0, 0],
      [2, 0, 0],
      [0, 0, 2],
      [0, 0, -2],
    ]);
    expect(sphere.center[0]).toBeCloseTo(0, 6);
    expect(sphere.center[1]).toBeCloseTo(0, 6);
    expect(sphere.center[2]).toBeCloseTo(0, 6);
    expect(sphere.radius).toBeCloseTo(2, 6);
  });

  it('is order-independent', () => {
    const a = computeBoundingSphere([
      [1, 0, 0],
      [4, 2, -1],
      [-3, 1, 5],
    ]);
    const b = computeBoundingSphere([
      [4, 2, -1],
      [-3, 1, 5],
      [1, 0, 0],
    ]);
    expect(a).toEqual(b);
  });
});

describe('computeFitDistance', () => {
  it('never solves closer than the effective-radius floor, even for a single node (radius 0)', () => {
    const farFloor = computeFitDistance(0, {
      minEffectiveRadius: 5,
      padding: 1,
      fovDegrees: 90,
      minDistance: 0,
      maxDistance: 1000,
    });
    // At fov=90 the half-angle is 45deg, so distance = radius / sin(45deg).
    expect(farFloor).toBeCloseTo(5 / Math.sin(Math.PI / 4), 4);
  });

  it('grows with radius (bigger real scenes still get pulled back)', () => {
    const near = computeFitDistance(2, { minDistance: 0, maxDistance: 1000 });
    const far = computeFitDistance(10, { minDistance: 0, maxDistance: 1000 });
    expect(far).toBeGreaterThan(near);
  });

  it('clamps to minDistance and maxDistance', () => {
    expect(computeFitDistance(0, { minEffectiveRadius: 0, minDistance: 4, maxDistance: 30 })).toBe(4);
    expect(computeFitDistance(1000, { minDistance: 4, maxDistance: 30 })).toBe(30);
  });

  it('a wider fov needs less distance to frame the same radius', () => {
    const narrow = computeFitDistance(5, { fovDegrees: 20, minDistance: 0, maxDistance: 1000 });
    const wide = computeFitDistance(5, { fovDegrees: 100, minDistance: 0, maxDistance: 1000 });
    expect(wide).toBeLessThan(narrow);
  });
});

describe('computeFitForPositions', () => {
  it('sparse (1 node) and busy (many nodes) scenes both resolve within clamps, sparse pulled closer', () => {
    const oneNode = computeFitForPositions([[0, 0, 0]], {
      minEffectiveRadius: 2,
      minDistance: 5,
      maxDistance: 14,
    });
    const manyNodes = computeFitForPositions(
      Array.from({ length: 20 }, (_, i) => [Math.cos(i) * 6, 0, Math.sin(i) * 6] as const),
      { minEffectiveRadius: 2, minDistance: 5, maxDistance: 14 },
    );

    // Sparse content still gets a comfortable, clamped distance (not glued
    // to the object) ...
    expect(oneNode.distance).toBeGreaterThanOrEqual(5);
    // ... but strictly less than a genuinely busy scene's distance, which is
    // exactly the "adapts to node count" behavior this exists for.
    expect(oneNode.distance).toBeLessThan(manyNodes.distance);
    expect(manyNodes.distance).toBeLessThanOrEqual(14);
  });

  it('four real nodes resolve closer than the busy-scene max, not lost at the far preset distance', () => {
    const fourNodes = computeFitForPositions(
      [
        [0, 0, 0],
        [3, 0, 0],
        [-3, 0, 0],
        [0, 0, 3],
      ],
      { minEffectiveRadius: 2, padding: 1.6, minDistance: 5.5, maxDistance: 13.4 },
    );
    expect(fourNodes.distance).toBeLessThan(13.4);
    expect(fourNodes.distance).toBeGreaterThanOrEqual(5.5);
  });
});
