import { useEffect } from 'react';
import { useGhostStore } from '../state/store';

/** When switching tabs, preserve world context for execution/evidence focus. */
export function useCrossTabFocus() {
  const mode = useGhostStore((s) => s.mode);

  useEffect(() => {
    const s = useGhostStore.getState();
    const worldId = s.selection?.kind === 'world' ? s.selection.id : s.focusedWorldId;
    if (!worldId) return;
    if (mode === 'execution') {
      s.focusWorld(worldId);
      s.setCameraLevel('execution');
    } else if (mode === 'evidence') {
      s.setSelection({ kind: 'world', id: worldId });
    }
  }, [mode]);
}
