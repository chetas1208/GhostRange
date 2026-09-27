import type { AppMode, CameraLevel, Selection } from '../state/types';

export type TourVariant = 'guided' | 'judge' | 'technical' | 'explore';

export type TourStatus = 'NOT_STARTED' | 'RUNNING' | 'PAUSED' | 'COMPLETED' | 'SKIPPED';

export type TourChapter =
  | 'INPUT'
  | 'UNDERSTAND'
  | 'INVESTIGATE'
  | 'EXECUTE'
  | 'VERIFY'
  | 'CONTROL'
  | 'PROVE';

export type TourInteraction =
  | 'select-auth-service'
  | 'select-cache-experiment'
  | 'select-active-worker'
  | 'select-final-claim'
  | 'build-investigation';

export type TourAnchorId =
  | 'tour-input-repo'
  | 'tour-input-incident'
  | 'tour-input-evidence'
  | 'production-world'
  | 'auth-service'
  | 'attack-path'
  | 'hypothesis-branch'
  | 'experiment-marker'
  | 'execution-dag'
  | 'critical-path'
  | 'scheduler-decision'
  | 'worker-active'
  | 'action-gate'
  | 'causal-path'
  | 'claim-root'
  | 'verification-ring';

export interface TourStepV1 {
  id: string;
  chapter: TourChapter;
  variants: TourVariant[];
  title: string;
  body: string;
  /** INPUT overlay vs 3D scene */
  surface?: 'input' | 'scene' | 'summary';
  mode?: AppMode;
  camera?: CameraLevel;
  replayMs?: number;
  anchor?: TourAnchorId;
  domAnchor?: string;
  interaction?: TourInteraction;
  autoAdvanceMs?: number;
  truthLabel?: string;
  showWhy?: boolean;
}

export interface TourCheckpoint {
  stepIndex: number;
  mode: AppMode;
  cameraLevel: CameraLevel;
  selection: Selection | null;
  replayMs: number;
  focusedWorldId: string | null;
}

export interface TourStateV1 {
  tour_id: string;
  tour_variant: TourVariant;
  chapter: TourChapter;
  step_id: string;
  status: TourStatus;
  step_index: number;
  controlled_campaign_id: string;
  completed_interactions: TourInteraction[];
  show_welcome: boolean;
  show_input: boolean;
  show_summary: boolean;
  explore_mode: boolean;
  show_why: boolean;
}
