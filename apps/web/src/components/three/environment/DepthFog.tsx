import { colors } from '@ghostrange/ui-3d';

/** Atmospheric depth — keeps negative space in the operational chamber. */
export function DepthFog() {
  return <fog attach="fog" args={[colors.void, 18, 55]} />;
}
