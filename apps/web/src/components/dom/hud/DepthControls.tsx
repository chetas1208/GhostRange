import { useGhostStore } from '../../../state/store';

/** §6 semantic depth — DOM equivalent of scroll dolly (no permanent sidebar). */
export function DepthControls() {
  const dolly = useGhostStore((s) => s.cameraDolly);
  const setCameraDolly = useGhostStore((s) => s.setCameraDolly);
  const pushCameraLevel = useGhostStore((s) => s.pushCameraLevel);
  const popCameraLevel = useGhostStore((s) => s.popCameraLevel);

  return (
    <div className="depth-controls hud" aria-label="Camera depth">
      <button type="button" aria-label="Zoom in" onClick={() => setCameraDolly(dolly + 1)}>
        +
      </button>
      <span className="depth-label">Depth</span>
      <button type="button" aria-label="Zoom out" onClick={() => setCameraDolly(Math.max(0, dolly - 1))}>
        −
      </button>
      <button type="button" aria-label="Focus inward" onClick={() => pushCameraLevel('network')}>
        In
      </button>
      <button type="button" aria-label="Focus outward" onClick={() => popCameraLevel()}>
        Out
      </button>
    </div>
  );
}
