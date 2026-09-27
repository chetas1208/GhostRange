import { invalidate } from '@react-three/fiber';
import { useEffect } from 'react';
import { useGhostStore } from '../state/store';

/** Re-render canvas on event stream updates (demand frameloop). */
export function useInvalidateOnEvents() {
  const sequence = useGhostStore((s) => s.sequence);

  useEffect(() => {
    invalidate();
  }, [sequence]);
}
