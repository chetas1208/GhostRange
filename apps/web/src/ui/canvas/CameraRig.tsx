import { useFrame, useThree } from '@react-three/fiber';
import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import { useGhostStore } from '../../state/store';

const PRESETS = {
  multiverse: { pos: [0, 6, 12] as const, target: [0, 0, 0] as const },
  execution: { pos: [0, 4, 10] as const, target: [0, 0, 0] as const },
  evidence: { pos: [0, 3, 8] as const, target: [0, 0.5, 0] as const },
  world: { pos: [0, 3.2, 7] as const, target: [0, 0.2, 0] as const },
  network: { pos: [0, 2.5, 4] as const, target: [0, 0.3, 0] as const },
  host: { pos: [0, 1.5, 2.5] as const, target: [0, 0.2, 0] as const },
  execution_micro: { pos: [0, 1, 1.8] as const, target: [0, 0.1, 0] as const },
};

export function CameraRig() {
  const mode = useGhostStore((s) => s.mode);
  const cameraLevel = useGhostStore((s) => s.cameraLevel);
  const focusedWorldId = useGhostStore((s) => s.focusedWorldId);
  const cameraDolly = useGhostStore((s) => s.cameraDolly);
  const reducedMotion = useReducedMotion();
  const { camera } = useThree();
  const target = useRef(new THREE.Vector3());
  const desired = useRef(new THREE.Vector3());

  useEffect(() => {
    const key =
      cameraLevel === 'execution'
        ? 'execution_micro'
        : cameraLevel === 'host'
          ? 'host'
          : cameraLevel === 'network'
            ? 'network'
            : cameraLevel === 'world' || focusedWorldId
              ? 'world'
              : mode;
    const preset = PRESETS[key as keyof typeof PRESETS] ?? PRESETS.multiverse;
    const dolly = 1 - Math.min(0.35, cameraDolly * 0.04);
    desired.current.set(preset.pos[0], preset.pos[1], preset.pos[2] * dolly);
    target.current.set(preset.target[0], preset.target[1], preset.target[2]);
    if (reducedMotion) {
      camera.position.copy(desired.current);
      camera.lookAt(target.current);
    }
  }, [mode, cameraLevel, focusedWorldId, cameraDolly, reducedMotion]);

  useFrame((_, delta) => {
    if (reducedMotion) return;
    const lerp = 1 - Math.exp(-4 * delta);
    camera.position.lerp(desired.current, lerp);
    camera.lookAt(target.current);
  });

  return null;
}
