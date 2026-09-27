import { useThree } from '@react-three/fiber';
import { useEffect } from 'react';

export type PerformanceGovernorProps = {
  maxDpr?: number;
};

export function PerformanceGovernor({ maxDpr = 1.5 }: PerformanceGovernorProps) {
  const gl = useThree((s) => s.gl);
  useEffect(() => {
    gl.setPixelRatio(Math.min(window.devicePixelRatio, maxDpr));
  }, [gl, maxDpr]);
  return null;
}
