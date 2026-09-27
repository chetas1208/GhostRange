import { useEffect, useRef } from 'react';
import type { AppMode } from '../state/types';
import { useGhostStore } from '../state/store';

const MODES: AppMode[] = ['multiverse', 'execution', 'evidence'];

function readParams(): URLSearchParams {
  return new URLSearchParams(window.location.search);
}

function applyParamsToStore() {
  const p = readParams();
  const tab = p.get('tab');
  if (tab && MODES.includes(tab as AppMode)) {
    useGhostStore.getState().setMode(tab as AppMode);
  }
  const world = p.get('world');
  if (world) {
    useGhostStore.getState().focusWorld(world);
    useGhostStore.getState().setSelection({ kind: 'world', id: world });
  }
  const rangeId = p.get('rangeId');
  if (rangeId && useGhostStore.getState().streamRangeId !== rangeId) {
    useGhostStore.setState({ streamRangeId: rangeId });
  }
  const claim = p.get('claim');
  if (claim) {
    useGhostStore.getState().setMode('evidence');
    useGhostStore.getState().setSelection({ kind: 'claim', id: claim });
  }
}

function writeParamsFromStore() {
  const s = useGhostStore.getState();
  const p = new URLSearchParams(window.location.search);
  p.set('tab', s.mode);
  const existingRange = p.get('rangeId') ?? s.streamRangeId;
  if (existingRange) p.set('rangeId', existingRange);
  if (s.selection?.kind === 'world') p.set('world', s.selection.id);
  else if (s.focusedWorldId) p.set('world', s.focusedWorldId);
  if (s.selection?.kind === 'claim') p.set('claim', s.selection.id);
  if (s.selection?.kind === 'task') p.set('task', s.selection.id);
  const next = `${window.location.pathname}?${p.toString()}`;
  if (next !== `${window.location.pathname}${window.location.search}`) {
    window.history.replaceState(null, '', next);
  }
}

/** Deep links: ?tab=multiverse&world=W-42 — refresh preserves context. */
export function useTacticalSelectionUrl() {
  const synced = useRef(false);

  useEffect(() => {
    applyParamsToStore();
    synced.current = true;
    const onPop = () => applyParamsToStore();
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  useEffect(() => {
    let mode = useGhostStore.getState().mode;
    let selection = useGhostStore.getState().selection;
    let focusedWorldId = useGhostStore.getState().focusedWorldId;
    return useGhostStore.subscribe((state) => {
      if (!synced.current) return;
      if (
        state.mode === mode &&
        state.selection === selection &&
        state.focusedWorldId === focusedWorldId
      ) {
        return;
      }
      mode = state.mode;
      selection = state.selection;
      focusedWorldId = state.focusedWorldId;
      writeParamsFromStore();
    });
  }, []);
}
