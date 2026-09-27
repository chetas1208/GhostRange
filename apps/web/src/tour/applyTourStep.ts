import { useGhostStore } from '../state/store';
import type { TourStepV1 } from './types';
import { loadTourControlledReplay, pauseTourReplay, seekTourReplay } from './tourReplay';

export async function applyTourStep(step: TourStepV1, opts: { firstScene?: boolean }) {
  if (step.surface === 'input') return;
  if (step.surface === 'summary') return;

  if (opts.firstScene) {
    await loadTourControlledReplay();
  } else {
    pauseTourReplay();
  }

  const store = useGhostStore.getState();
  if (step.mode) store.setMode(step.mode);
  if (step.camera) store.setCameraLevel(step.camera);
  if (step.replayMs != null) {
    seekTourReplay(step.replayMs);
  }

  if (step.id === 'living-twin') {
    store.focusWorld(null);
    store.clearSelection();
  }
  if (step.id === 'attack-path') {
    store.setSelection({ kind: 'attack', id: 'world-base', worldId: 'world-base' });
    store.focusWorld('world-base');
  }
  if (step.id === 'scheduler-decision') {
    store.setSelection({ kind: 'decision', id: 'd-gpu' });
  }
  if (step.id === 'select-worker' || step.id === 'worker-lifecycle') {
    store.setSelection(null);
  }
  if (step.id === 'evidence-mode' || step.id === 'select-claim') {
    store.setSelection({ kind: 'claim', id: 'claim-b' });
  }
  if (step.id === 'causal') {
    useGhostStore.setState({
      causal: {
        label: 'session_refresh_cache',
        cacheBlocks: true,
        transportC: 'intervention-supported',
        rejectsCTransport: false,
      },
    });
  }
  if (step.id === 'shield-deny') {
    useGhostStore.setState({
      authorizationGate: {
        position: [-2, 0.6, -8],
        state: 'DENIED',
        actionType: 'CREATE_GPU_WORKERS',
        reason: 'Worker limit and budget policy',
      },
    });
  }
}
