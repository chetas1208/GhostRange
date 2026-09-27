/**
 * Reads the shared `--gr-motion-scale` CSS var (set by the host app's
 * reduced-motion hook — see `apps/web/src/hooks/useReducedMotionGlobally.ts`)
 * so purely-decorative ambient motion in this package can honor
 * `prefers-reduced-motion` without each primitive owning its own media-query
 * listener. 1 = full motion, 0 = reduced-motion is on and decoration should
 * hold still. Intended to be read fresh inside `useFrame` (not as React
 * state) since it changes rarely and the read itself must not trigger
 * re-renders.
 *
 * This never gates status-bearing visual state (color/material swaps) — per
 * INTERACTION_MODEL.md, motion here is decoration on top of an
 * already-legible status cue, never the only channel for information.
 */
export function readMotionScale(): number {
  if (typeof document === 'undefined') return 1;
  const raw = getComputedStyle(document.documentElement).getPropertyValue('--gr-motion-scale');
  const value = parseFloat(raw);
  return Number.isFinite(value) ? value : 1;
}
