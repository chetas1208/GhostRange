import { create } from 'zustand';
import { applyEvents, createInitialState, reduceEvent } from './eventReducer';
import { buildSelectionSummary } from './selectionSummary';
import type {
  AppMode,
  CameraLevel,
  GhostEvent,
  GhostState,
  GhostWatchSummaryV1,
  MeshSummaryV1,
  CausalSummaryV1,
  PromotionSummaryV1,
  Selection,
} from './types';

export interface GhostStore extends GhostState {
  dispatchEvent: (event: GhostEvent) => void;
  dispatchEvents: (events: GhostEvent[]) => void;
  reset: () => void;
  setMode: (mode: AppMode) => void;
  setSelection: (selection: Selection | null) => void;
  resetToMultiverseOverview: () => void;
  setCameraLevel: (level: CameraLevel) => void;
  focusWorld: (worldId: string | null) => void;
  setReplayTimeMs: (ms: number) => void;
  popCameraLevel: () => void;
  pushCameraLevel: (level: CameraLevel) => void;
  setHoverTarget: (selection: Selection | null) => void;
  setStreamError: (message: string | null) => void;
  clearSelection: () => void;
  setCameraDolly: (dolly: number) => void;
  setPromotion: (promotion: PromotionSummaryV1 | null) => void;
  setGhostwatch: (ghostwatch: GhostWatchSummaryV1 | null) => void;
  setMesh: (mesh: MeshSummaryV1 | null) => void;
  setCausal: (causal: CausalSummaryV1 | null) => void;
}

export const useGhostStore = create<GhostStore>((set, get) => ({
  ...createInitialState(),
  dispatchEvent: (event) => set((s) => reduceEvent(s, event)),
  dispatchEvents: (events) =>
    set((s) => {
      const next = applyEvents(s, events);
      if (s.dataSource !== 'live' || events.length === 0) return next;
      const liveEventBuffer = [...s.liveEventBuffer, ...events].slice(-1200);
      const replayMaxMs = Math.max(s.replayMaxMs, liveEventBuffer.length * 1500);
      return { ...next, liveEventBuffer, replayMaxMs };
    }),
  reset: () => set(createInitialState()),
  setMode: (mode) => set({ mode }),
  setSelection: (selection) =>
    set((s) => ({
      selection,
      ariaSelectionSummary: buildSelectionSummary(s, selection),
    })),
  resetToMultiverseOverview: () =>
    set({
      mode: 'multiverse',
      selection: null,
      focusedWorldId: null,
      cameraLevel: 'multiverse',
      ariaSelectionSummary: '',
    }),
  setCameraLevel: (cameraLevel) => set({ cameraLevel }),
  focusWorld: (focusedWorldId) => set({ focusedWorldId, cameraLevel: focusedWorldId ? 'world' : 'multiverse' }),
  setReplayTimeMs: (replayTimeMs) => set({ replayTimeMs, replayScrubbing: true }),
  popCameraLevel: () => {
    const order: CameraLevel[] = ['execution', 'host', 'network', 'world', 'multiverse'];
    const idx = order.indexOf(get().cameraLevel);
    set({ cameraLevel: order[Math.min(order.length - 1, idx + 1)] ?? 'multiverse' });
  },
  pushCameraLevel: (level) => set({ cameraLevel: level }),
  setHoverTarget: (hoverTarget) => set({ hoverTarget }),
  setStreamError: (streamError) => set({ streamError }),
  clearSelection: () =>
    set({
      selection: null,
      hoverTarget: null,
      ariaSelectionSummary: '',
    }),
  setCameraDolly: (cameraDolly) => set({ cameraDolly }),
  setPromotion: (promotion) =>
    set({
      promotion: promotion ? { ...promotion, showProductionShadow: true } : null,
    }),
  setGhostwatch: (ghostwatch) => set({ ghostwatch }),
  setMesh: (mesh) => set({ mesh }),
  setCausal: (causal) => set({ causal }),
}));
