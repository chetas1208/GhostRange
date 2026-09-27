import { useFrame } from '@react-three/fiber';
import { useMemo, useRef } from 'react';
import { Object3D } from 'three';
import type { InstancedMesh } from 'three';
import { colors } from '../materials/theme';
import { readMotionScale } from '../shared/motionScale';

export type AmbientFieldProps = {
  /** Hard cap on visible particles — ambient dressing must never scale with scene complexity. */
  count?: number;
  /** Radius (scene units) of the shell the field drifts within. */
  radius?: number;
};

/** Absolute ceiling regardless of `count`, matching the perf budget's capped-particle-count discipline. */
const MAX_COUNT = 90;

/**
 * Ambient depth-and-scale dressing for the void: a fixed, hard-capped
 * particle shell that gives every scene a sense of presence and place
 * independent of how many real entities are currently materialized.
 *
 * This is purely decorative — it carries no domain state, never represents
 * a real entity, and is not gated on any backend event (unlike every
 * "materializes only after a real event" primitive elsewhere in this
 * package). Its job is to keep a scene with 1-4 real nodes reading as "a
 * real, small, live system in a real space" rather than "an empty void
 * something failed to load into" — see THREE_D_ARCHITECTURE.md §8's
 * capped-particle-count requirement, which this follows (one instanced
 * draw call, count clamped, decorative motion mutes under
 * `prefers-reduced-motion` via the shared `--gr-motion-scale` var).
 */
export function AmbientField({ count = 70, radius = 20 }: AmbientFieldProps) {
  const active = Math.min(MAX_COUNT, Math.max(0, count));
  const mesh = useRef<InstancedMesh>(null);
  const t = useRef(0);
  const dummy = useMemo(() => new Object3D(), []);

  const seeds = useMemo(() => {
    const out: { theta: number; phi: number; r: number; speed: number; scale: number }[] = [];
    for (let i = 0; i < MAX_COUNT; i++) {
      // Deterministic pseudo-random spread — this is decoration, not
      // domain data, so a stable low-discrepancy sequence (no Math.random)
      // keeps the field the same shape across remounts/tests.
      out.push({
        theta: (i * 2.399963) % (Math.PI * 2),
        phi: (((i * 0.618034) % 1) - 0.5) * Math.PI,
        r: 0.55 + ((i * 37) % 100) / 100,
        speed: 0.05 + ((i * 13) % 10) / 100,
        scale: 0.02 + ((i * 7) % 10) / 400,
      });
    }
    return out;
  }, []);

  useFrame((_, delta) => {
    if (!mesh.current) return;
    mesh.current.count = active;
    if (active <= 0) return;
    t.current += delta * readMotionScale();
    for (let i = 0; i < active; i++) {
      const s = seeds[i];
      const r = radius * s.r;
      const drift = Math.sin(t.current * s.speed + i) * 0.5;
      dummy.position.set(
        Math.cos(s.theta) * Math.cos(s.phi) * r,
        Math.sin(s.phi) * r * 0.4 + drift,
        Math.sin(s.theta) * Math.cos(s.phi) * r,
      );
      dummy.scale.setScalar(s.scale);
      dummy.updateMatrix();
      mesh.current.setMatrixAt(i, dummy.matrix);
    }
    mesh.current.instanceMatrix.needsUpdate = true;
  });

  if (active <= 0) return null;

  return (
    <instancedMesh ref={mesh} args={[undefined, undefined, MAX_COUNT]} frustumCulled={false}>
      <sphereGeometry args={[1, 5, 5]} />
      <meshBasicMaterial color={colors.link} transparent opacity={0.22} depthWrite={false} />
    </instancedMesh>
  );
}
