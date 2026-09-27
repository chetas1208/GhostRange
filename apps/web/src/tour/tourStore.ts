import { create } from 'zustand';
import type { TourCheckpoint, TourInteraction, TourStatus, TourVariant } from './types';
import { GUIDED_TOUR_STEPS, stepsForVariant, TOUR_CAMPAIGN_ID } from './steps/guidedSteps';

const LS_KEY = 'ghostrange.tour.completed';

export interface TourStore {
  status: TourStatus;
  variant: TourVariant;
  stepIndex: number;
  showWelcome: boolean;
  showInput: boolean;
  showSummary: boolean;
  exploreMode: boolean;
  showWhy: boolean;
  completedInteractions: TourInteraction[];
  checkpoints: TourCheckpoint[];
  isTourSession: boolean;

  steps: () => ReturnType<typeof stepsForVariant>;
  currentStep: () => (typeof GUIDED_TOUR_STEPS)[number] | undefined;

  openWelcome: () => void;
  dismissWelcomeExplore: () => void;
  startTour: (variant?: TourVariant) => void;
  skipTour: () => void;
  pauseTour: () => void;
  resumeTour: () => void;
  nextStep: () => void;
  backStep: () => void;
  restartTour: () => void;
  completeTour: () => void;
  markInteraction: (id: TourInteraction) => void;
  setShowWhy: (v: boolean) => void;
  finishInputChapter: () => void;
}

export const useTourStore = create<TourStore>((set, get) => ({
  status: 'NOT_STARTED',
  variant: 'guided',
  stepIndex: 0,
  showWelcome:
    import.meta.env.VITE_ENABLE_TOUR !== 'false' &&
    typeof localStorage !== 'undefined' &&
    localStorage.getItem(LS_KEY) !== '1',
  showInput: false,
  showSummary: false,
  exploreMode: false,
  showWhy: false,
  completedInteractions: [],
  checkpoints: [],
  isTourSession: false,

  steps: () => stepsForVariant(get().variant),
  currentStep: () => get().steps()[get().stepIndex],

  openWelcome: () => set({ showWelcome: true }),
  dismissWelcomeExplore: () => {
    localStorage.setItem(LS_KEY, '1');
    set({ showWelcome: false, exploreMode: true, isTourSession: false });
  },

  startTour: (variant = 'guided') => {
    localStorage.setItem(LS_KEY, '1');
    set({
      status: 'RUNNING',
      variant,
      stepIndex: 0,
      showWelcome: false,
      showInput: true,
      showSummary: false,
      exploreMode: false,
      showWhy: false,
      completedInteractions: [],
      checkpoints: [],
      isTourSession: true,
    });
  },

  skipTour: () => {
    localStorage.setItem(LS_KEY, '1');
    set({
      status: 'SKIPPED',
      showWelcome: false,
      showInput: false,
      showSummary: false,
      isTourSession: false,
    });
  },

  pauseTour: () => set({ status: 'PAUSED' }),
  resumeTour: () => set({ status: 'RUNNING' }),

  nextStep: () => {
    const steps = get().steps();
    const idx = get().stepIndex;
    if (idx >= steps.length - 1) {
      get().completeTour();
      return;
    }
    set({ stepIndex: idx + 1, showWhy: false });
  },

  backStep: () => {
    const idx = get().stepIndex;
    if (idx <= 0) return;
    set({ stepIndex: idx - 1, showWhy: false });
  },

  restartTour: () => {
    get().startTour(get().variant);
  },

  completeTour: () => {
    set({ status: 'COMPLETED', showSummary: true, showInput: false, isTourSession: false });
  },

  markInteraction: (id) =>
    set((s) => ({
      completedInteractions: s.completedInteractions.includes(id)
        ? s.completedInteractions
        : [...s.completedInteractions, id],
    })),

  setShowWhy: (v) => set({ showWhy: v }),

  finishInputChapter: () => set({ showInput: false }),
}));

export function selectTourActive() {
  return useTourStore.getState().isTourSession && useTourStore.getState().status === 'RUNNING';
}

export function tourCampaignId() {
  return TOUR_CAMPAIGN_ID;
}
