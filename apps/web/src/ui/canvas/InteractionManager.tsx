import { useThree } from '@react-three/fiber';
import { useEffect } from 'react';
import { fixtureReplayerRef } from '../../state/fixtureReplayerRef';
import { useGhostStore } from '../../state/store';

export function InteractionManager() {
  const gl = useThree((s) => s.gl);
  const popCameraLevel = useGhostStore((s) => s.popCameraLevel);
  const pushCameraLevel = useGhostStore((s) => s.pushCameraLevel);
  const cameraLevel = useGhostStore((s) => s.cameraLevel);
  const reset = useGhostStore((s) => s.reset);
  const dispatchEvents = useGhostStore((s) => s.dispatchEvents);
  const setReplayTimeMs = useGhostStore((s) => s.setReplayTimeMs);
  const replayMaxMs = useGhostStore((s) => s.replayMaxMs);
  const replayTimeMs = useGhostStore((s) => s.replayTimeMs);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') popCameraLevel();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [popCameraLevel]);

  useEffect(() => {
    const el = gl.domElement;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      if (e.shiftKey) {
        const delta = e.deltaY * 20;
        const ms = Math.max(0, Math.min(replayMaxMs, replayTimeMs + delta));
        fixtureReplayerRef.current?.seek(ms, reset, (events, t) => {
          dispatchEvents(events);
          setReplayTimeMs(t);
        });
        return;
      }
      const order = ['multiverse', 'world', 'network', 'host', 'execution'] as const;
      const idx = order.indexOf(cameraLevel);
      if (e.deltaY > 0 && idx < order.length - 1) pushCameraLevel(order[idx + 1]);
      if (e.deltaY < 0 && idx > 0) pushCameraLevel(order[idx - 1]);
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, [gl, cameraLevel, pushCameraLevel, replayMaxMs, replayTimeMs, setReplayTimeMs]);

  return null;
}
