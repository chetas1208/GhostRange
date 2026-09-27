/**
 * Pure camera-framing math shared by CameraRig.
 *
 * Why this exists: the per-mode camera presets in CameraRig.tsx were tuned
 * for a "busy" scene (many worlds/workers/tasks). A real investigation can
 * just as easily have 1-4 real nodes (e.g. one live compute worker, a
 * handful of forked worlds) — with a fixed preset distance that reads as
 * "tiny cluster lost in a vast void," i.e. broken, not "a real, small, live
 * system." This module computes a camera distance from the *actual* node
 * positions so the overview cameras (Multiverse/Execution/Evidence) fit
 * whatever is really there, with a deliberate floor so sparse scenes still
 * get comfortable negative space rather than an uncomfortably tight crop.
 *
 * Kept dependency-free (no three.js/R3F imports) so it's trivially unit
 * testable without a renderer.
 */

export type Vec3 = readonly [number, number, number];

/**
 * Chunks a flat `[x0,y0,z0, x1,y1,z1, ...]` array (the shape the store's
 * camera-fit selectors return — see the comment in `state/selectors.ts` for
 * why they're flat rather than an array of tuples) back into `Vec3`s for the
 * bounding-sphere math below.
 */
export function chunkVec3(flat: readonly number[]): Vec3[] {
  const out: Vec3[] = [];
  for (let i = 0; i + 2 < flat.length; i += 3) {
    out.push([flat[i], flat[i + 1], flat[i + 2]]);
  }
  return out;
}

export interface BoundingSphere {
  center: Vec3;
  radius: number;
}

/**
 * Centroid + max-distance-from-centroid over a set of node positions.
 * Deterministic and order-independent. An empty input collapses to a
 * zero-radius sphere at the origin.
 */
export function computeBoundingSphere(positions: readonly Vec3[]): BoundingSphere {
  if (positions.length === 0) {
    return { center: [0, 0, 0], radius: 0 };
  }

  let sx = 0;
  let sy = 0;
  let sz = 0;
  for (const [x, y, z] of positions) {
    sx += x;
    sy += y;
    sz += z;
  }
  const n = positions.length;
  const center: Vec3 = [sx / n, sy / n, sz / n];

  let maxDistSq = 0;
  for (const [x, y, z] of positions) {
    const dx = x - center[0];
    const dy = y - center[1];
    const dz = z - center[2];
    const distSq = dx * dx + dy * dy + dz * dz;
    if (distSq > maxDistSq) maxDistSq = distSq;
  }

  return { center, radius: Math.sqrt(maxDistSq) };
}

export interface FitDistanceOptions {
  /** Vertical field of view in degrees — should match the R3F camera's `fov`. */
  fovDegrees?: number;
  /** Multiplier on the fitted radius before solving distance; >1 leaves headroom around content. */
  padding?: number;
  /**
   * Floor on the radius used to solve distance. This is the deliberate
   * "premium at low node count" knob: without it, a 1-node scene (radius 0)
   * would solve to `minDistance`, jamming the camera right up against a
   * single node. The floor makes 1-4 nodes read as "a real, small, contained
   * system" with real negative space around it, not a zoomed-in crop.
   */
  minEffectiveRadius?: number;
  minDistance?: number;
  maxDistance?: number;
}

const DEFAULT_OPTIONS: Required<FitDistanceOptions> = {
  fovDegrees: 45,
  padding: 1.5,
  minEffectiveRadius: 2,
  minDistance: 3,
  maxDistance: 30,
};

/** Distance a camera at `fovDegrees` needs to fully frame a sphere of `radius`, then clamped. */
export function computeFitDistance(radius: number, options: FitDistanceOptions = {}): number {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  const effectiveRadius = Math.max(radius, opts.minEffectiveRadius, 0);
  const halfFovRad = (opts.fovDegrees * Math.PI) / 360;
  const distance = (effectiveRadius * opts.padding) / Math.sin(halfFovRad);
  return clamp(distance, opts.minDistance, opts.maxDistance);
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export interface CameraFit {
  center: Vec3;
  distance: number;
}

/** Bounding sphere over `positions`, resolved straight to a clamped camera distance + look-at center. */
export function computeFitForPositions(positions: readonly Vec3[], options?: FitDistanceOptions): CameraFit {
  const { center, radius } = computeBoundingSphere(positions);
  return { center, distance: computeFitDistance(radius, options) };
}
