import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import type { SemanticState } from '../materials/theme';

export type SemanticMotionRef = {
  t: number;
  ripple: number;
  pulse: number;
  fracture: number;
  contract: number;
};

/**
 * Motion samples live in a ref updated in useFrame only — never read during React render
 * (reading animated values in render caused React #185 / max update depth with R3F + Zustand).
 */
export function useSemanticMotion(state: SemanticState, speed = 1) {
  const motion = useRef<SemanticMotionRef>({
    t: 0,
    ripple: 0,
    pulse: 0,
    fracture: state === 'failed' ? 0.15 : 0,
    contract: 0,
  });

  useFrame((_, delta) => {
    motion.current.t += delta * speed;
    const t = motion.current.t;
    motion.current.ripple = state === 'investigating' ? Math.sin(t * 2) * 0.02 : 0;
    motion.current.pulse = state === 'verifying' || state === 'provisioning' ? 0.5 + Math.sin(t * 3) * 0.5 : 0;
    motion.current.fracture = state === 'failed' ? 0.15 : 0;
    motion.current.contract = state === 'pruned' ? Math.min(1, t * 0.5) : 0;
  });

  return motion;
}
