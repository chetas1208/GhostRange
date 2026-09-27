import { useFrame, useThree } from '@react-three/fiber';
import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { useShallow } from 'zustand/react/shallow';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import { useGhostStore } from '../../state/store';
import {
  selectEvidenceNodePositions,
  selectExecutionNodePositions,
  selectMultiverseNodePositions,
} from '../../state/selectors';
import { chunkVec3, computeFitForPositions, type FitDistanceOptions } from './cameraFraming';

const PRESETS = {
  multiverse: { pos: [0, 6, 12] as const, target: [0, 0, 0] as const },
  execution: { pos: [0, 4, 10] as const, target: [0, 0, 0] as const },
  evidence: { pos: [0, 3, 8] as const, target: [0, 0.5, 0] as const },
  world: { pos: [0, 3.2, 7] as const, target: [0, 0.2, 0] as const },
  network: { pos: [0, 2.5, 4] as const, target: [0, 0.3, 0] as const },
  host: { pos: [0, 1.5, 2.5] as const, target: [0, 0.2, 0] as const },
  execution_micro: { pos: [0, 1, 1.8] as const, target: [0, 0.1, 0] as const },
};

// Per-mode fit tuning for the overview cameras. `maxDistance` is set at (or
// just under) each mode's original fixed preset magnitude, so a genuinely
// busy scene frames about the same as before; `minEffectiveRadius`/
// `minDistance` are the "premium at low node count" floor — they keep 1-4
// real nodes from either vanishing into a wide shot or getting jammed
// uncomfortably close (see cameraFraming.ts).
const FIT_OPTIONS: Record<'multiverse' | 'execution' | 'evidence', FitDistanceOptions> = {
  multiverse: { fovDegrees: 45, padding: 1.6, minEffectiveRadius: 2, minDistance: 5.5, maxDistance: 13.4 },
  execution: { fovDegrees: 45, padding: 1.6, minEffectiveRadius: 1.8, minDistance: 4.5, maxDistance: 10.8 },
  evidence: { fovDegrees: 45, padding: 1.7, minEffectiveRadius: 1.5, minDistance: 4, maxDistance: 8.5 },
};

export function CameraRig() {
  const mode = useGhostStore((s) => s.mode);
  const cameraLevel = useGhostStore((s) => s.cameraLevel);
  const focusedWorldId = useGhostStore((s) => s.focusedWorldId);
  const cameraDolly = useGhostStore((s) => s.cameraDolly);
  const multiversePositions = useGhostStore(useShallow(selectMultiverseNodePositions));
  const executionPositions = useGhostStore(useShallow(selectExecutionNodePositions));
  const evidencePositions = useGhostStore(useShallow(selectEvidenceNodePositions));
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
    const drilledIn = key !== mode;

    if (drilledIn) {
      // Unchanged: a drill-down frames one known entity's fixed cinematic
      // pose, which isn't a function of ambient node-count sparsity.
      desired.current.set(preset.pos[0], preset.pos[1], preset.pos[2] * dolly);
      target.current.set(preset.target[0], preset.target[1], preset.target[2]);
    } else {
      const flatPositions =
        mode === 'multiverse'
          ? multiversePositions
          : mode === 'execution'
            ? executionPositions
            : evidencePositions;
      const fit = computeFitForPositions(chunkVec3(flatPositions), FIT_OPTIONS[mode as keyof typeof FIT_OPTIONS]);
      const dirLen = Math.hypot(preset.pos[0], preset.pos[1], preset.pos[2]) || 1;
      const distance = fit.distance * dolly;
      desired.current.set(
        (preset.pos[0] / dirLen) * distance,
        (preset.pos[1] / dirLen) * distance,
        (preset.pos[2] / dirLen) * distance,
      );
      target.current.set(fit.center[0], preset.target[1], fit.center[2]);
    }

    if (reducedMotion) {
      camera.position.copy(desired.current);
      camera.lookAt(target.current);
    }
  }, [
    mode,
    cameraLevel,
    focusedWorldId,
    cameraDolly,
    reducedMotion,
    multiversePositions,
    executionPositions,
    evidencePositions,
  ]);

  useFrame((_, delta) => {
    if (reducedMotion) return;
    const lerp = 1 - Math.exp(-4 * delta);
    camera.position.lerp(desired.current, lerp);
    camera.lookAt(target.current);
  });

  return null;
}
