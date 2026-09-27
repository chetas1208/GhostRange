import { OrbitControls } from '@react-three/drei';
import { useMemo } from 'react';
import { MultiverseScene } from '../scenes/MultiverseScene';
import { ExecutionScene } from '../scenes/ExecutionScene';
import { EvidenceScene } from '../scenes/EvidenceScene';
import { OriginMarker, SpatialTimeline } from '@ghostrange/ui-3d';
import { selectHasActiveWorld } from '../../state/selectors';
import { useGhostStore } from '../../state/store';

export function SceneRoot() {
  const showOrigin = useGhostStore((s) => !selectHasActiveWorld(s));
  const timelineMarkers = useGhostStore((s) => s.timelineMarkers);
  const markers = useMemo(
    () =>
      timelineMarkers.map((m, i) => ({
        t: m.t,
        position: [-3 + i * 1.2, 0, 0] as [number, number, number],
      })),
    [timelineMarkers],
  );

  return (
    <>
      <OrbitControls enablePan={false} maxPolarAngle={Math.PI / 2.1} minDistance={3} maxDistance={24} />
      {showOrigin && <OriginMarker />}
      <MultiverseScene />
      <ExecutionScene />
      <EvidenceScene />
      <SpatialTimeline markers={markers} />
    </>
  );
}
