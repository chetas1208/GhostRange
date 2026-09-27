import { useEffect, useMemo, type ReactNode } from 'react';
import { useGhostStore } from '../state/store';
import { applyTourStep } from './applyTourStep';
import { TourCallout } from './components/TourCallout';
import { TourInputPanel } from './components/TourInputPanel';
import { TourSpotlight } from './components/TourSpotlight';
import { TourSummary } from './components/TourSummary';
import { TourWelcome } from './components/TourWelcome';
import { destroyTourReplay } from './tourReplay';
import { useTourStore } from './tourStore';
import type { TourInteraction } from './types';

function interactionSatisfied(
  id: TourInteraction,
  completed: TourInteraction[],
  selection: ReturnType<typeof useGhostStore.getState>['selection'],
): boolean {
  if (completed.includes(id)) return true;
  switch (id) {
    case 'build-investigation':
      return completed.includes('build-investigation');
    case 'select-auth-service':
      return selection?.kind === 'asset' && selection.id === 'a-auth';
    case 'select-cache-experiment':
      return selection?.kind === 'task' && (selection.id === 't17' || selection.id === 't-c-stop');
    case 'select-active-worker':
      return selection?.kind === 'worker' && ['w1', 'w2', 'w3', 'w4'].includes(selection.id);
    case 'select-final-claim':
      return selection?.kind === 'claim' && selection.id === 'claim-b';
    default:
      return true;
  }
}

export function TourProvider({ children }: { children: ReactNode }) {
  const status = useTourStore((s) => s.status);
  const stepIndex = useTourStore((s) => s.stepIndex);
  const steps = useTourStore((s) => s.steps());
  const step = steps[stepIndex];
  const completedInteractions = useTourStore((s) => s.completedInteractions);
  const showWhy = useTourStore((s) => s.showWhy);
  const selection = useGhostStore((s) => s.selection);

  const next = useTourStore((s) => s.nextStep);
  const back = useTourStore((s) => s.backStep);
  const skip = useTourStore((s) => s.skipTour);
  const pause = useTourStore((s) => s.pauseTour);
  const resume = useTourStore((s) => s.resumeTour);
  const setShowWhy = useTourStore((s) => s.setShowWhy);
  const markInteraction = useTourStore((s) => s.markInteraction);

  useEffect(() => {
    if (status !== 'RUNNING' || !step || step.surface !== 'scene') return;
    void applyTourStep(step, { firstScene: step.id === 'living-twin' });
  }, [status, step?.id]);

  useEffect(() => {
    if (status !== 'RUNNING' || !step?.interaction) return;
    if (interactionSatisfied(step.interaction, completedInteractions, selection)) {
      markInteraction(step.interaction);
    }
  }, [status, step?.interaction, selection, completedInteractions, markInteraction]);

  useEffect(() => {
    return () => {
      if (useTourStore.getState().status === 'SKIPPED') destroyTourReplay();
    };
  }, []);

  const canNext = useMemo(() => {
    if (!step?.interaction) return true;
    return interactionSatisfied(step.interaction, completedInteractions, selection);
  }, [step, completedInteractions, selection]);

  const showCallout = (status === 'RUNNING' || status === 'PAUSED') && step && step.surface !== 'summary';

  return (
    <>
      {children}
      <TourWelcome />
      <TourInputPanel />
      {status === 'PAUSED' ? (
        <div className="tour-paused">
          <span>Tour paused</span>
          <button type="button" className="tour-btn primary" onClick={resume}>
            Resume tour
          </button>
        </div>
      ) : null}
      {showCallout && status === 'RUNNING' ? (
        <>
          <TourSpotlight anchor={step.anchor} />
          <TourCallout
            step={step}
            stepIndex={stepIndex}
            stepCount={steps.length}
            canNext={canNext}
            onNext={next}
            onBack={back}
            onSkip={skip}
            onPause={pause}
            onShowWhy={step.showWhy ? () => setShowWhy(!showWhy) : undefined}
            showWhy={showWhy}
          />
        </>
      ) : null}
      <TourSummary />
    </>
  );
}
