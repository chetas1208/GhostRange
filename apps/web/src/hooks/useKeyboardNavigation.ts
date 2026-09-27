import { useEffect } from 'react';
import type { AppMode } from '../state/types';
import { useGhostStore } from '../state/store';

const MODE_KEYS: Record<string, AppMode> = {
  '1': 'multiverse',
  '2': 'execution',
  '3': 'evidence',
};

export function useKeyboardNavigation() {
  const setMode = useGhostStore((s) => s.setMode);
  const popCameraLevel = useGhostStore((s) => s.popCameraLevel);
  const clearSelection = useGhostStore((s) => s.clearSelection);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (MODE_KEYS[e.key]) {
        setMode(MODE_KEYS[e.key]);
        return;
      }
      if (e.key === 'Escape') {
        clearSelection();
        popCameraLevel();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [popCameraLevel, setMode, clearSelection]);
}
