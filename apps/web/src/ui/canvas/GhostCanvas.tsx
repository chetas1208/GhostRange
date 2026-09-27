import { Canvas } from '@react-three/fiber';
import { EffectComposer, Bloom } from '@react-three/postprocessing';
import { AmbientField, PerformanceGovernor, ReferenceGrid, colors } from '@ghostrange/ui-3d';
import { CameraRig } from './CameraRig';
import { InteractionManager } from './InteractionManager';
import { LightingRig } from './LightingRig';
import { SceneRoot } from './SceneRoot';
import { DepthFog } from '../../components/three/environment/DepthFog';
import { useInvalidateOnEvents } from '../../hooks/useInvalidateOnEvents';
import { useGhostStore } from '../../state/store';
import {
  selectAnyActiveAttack,
  selectAnyWorkerProvisioning,
  selectAnyWorldVerifying,
  selectConnectionStatus,
} from '../../state/selectors';

function BloomGate() {
  const selection = useGhostStore((s) => s.selection);
  const attacks = useGhostStore(selectAnyActiveAttack);
  const provisioning = useGhostStore(selectAnyWorkerProvisioning);
  const verifying = useGhostStore(selectAnyWorldVerifying);
  const on = Boolean(selection || attacks || provisioning || verifying);
  if (!on) return null;
  return (
    <EffectComposer>
      <Bloom intensity={0.35} luminanceThreshold={0.6} luminanceSmoothing={0.2} />
    </EffectComposer>
  );
}

function CanvasInner() {
  useInvalidateOnEvents();
  return null;
}

export function GhostCanvas() {
  const disconnected = useGhostStore((s) => selectConnectionStatus(s) === 'DISCONNECTED');
  const clearSelection = useGhostStore((s) => s.clearSelection);
  return (
    <Canvas
      camera={{ position: [0, 6, 12], fov: 45, near: 0.1, far: 200 }}
      frameloop="demand"
      gl={{ antialias: true, alpha: false }}
      onPointerMissed={() => clearSelection()}
      style={{
        background: colors.void,
        filter: disconnected ? 'saturate(0.35) contrast(0.92)' : undefined,
        transition: 'filter 0.4s ease',
      }}
    >
      <color attach="background" args={[colors.void]} />
      <CanvasInner />
      <PerformanceGovernor maxDpr={1.5} />
      <LightingRig />
      <DepthFog />
      <ReferenceGrid />
      <AmbientField />
      <SceneRoot />
      <CameraRig />
      <InteractionManager />
      <BloomGate />
    </Canvas>
  );
}
