import { useEffect } from 'react';
import { useReducedMotion } from './useReducedMotion';

/** Disables decorative motion in store-driven UI when user prefers reduced motion (§18). */
export function useReducedMotionGlobally() {
  const reduced = useReducedMotion();

  useEffect(() => {
    document.documentElement.style.setProperty('--gr-motion-scale', reduced ? '0' : '1');
  }, [reduced]);

  return reduced;
}
