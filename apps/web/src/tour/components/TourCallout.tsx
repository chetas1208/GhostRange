import { useEffect, useRef, type CSSProperties } from 'react';
import { getTourAnchorScreenPos } from '../anchorRegistry';
import type { TourStepV1 } from '../types';
import { TourProgress } from './TourProgress';

export function TourCallout({
  step,
  stepIndex,
  stepCount,
  canNext,
  onNext,
  onBack,
  onSkip,
  onPause,
  onShowWhy,
  showWhy,
}: {
  step: TourStepV1;
  stepIndex: number;
  stepCount: number;
  canNext: boolean;
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
  onPause: () => void;
  onShowWhy?: () => void;
  showWhy?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const anchor = step.anchor ? getTourAnchorScreenPos(step.anchor) : null;
  const domEl = step.domAnchor ? document.querySelector(`[data-tour-anchor="${step.domAnchor}"]`) : null;

  useEffect(() => {
    ref.current?.focus();
  }, [step.id]);

  let style: CSSProperties = { bottom: '5.5rem', left: '1.25rem', maxWidth: '22rem' };
  if (anchor?.visible) {
    style = {
      top: Math.min(window.innerHeight - 220, Math.max(80, anchor.y - 20)),
      left: Math.min(window.innerWidth - 360, Math.max(16, anchor.x - 180)),
      maxWidth: '22rem',
    };
  } else if (domEl) {
    const r = domEl.getBoundingClientRect();
    style = { top: r.bottom + 12, left: r.left, maxWidth: '22rem' };
  }

  return (
    <div
      ref={ref}
      className="tour-callout"
      style={style}
      role="region"
      aria-labelledby={`tour-step-title-${step.id}`}
      tabIndex={-1}
    >
      <TourProgress chapter={step.chapter} />
      {step.truthLabel ? <span className="tour-truth">{step.truthLabel}</span> : null}
      <h2 id={`tour-step-title-${step.id}`}>{step.title}</h2>
      <p>{step.body}</p>
      {step.showWhy && onShowWhy ? (
        <button type="button" className="tour-btn ghost" onClick={onShowWhy}>
          {showWhy ? 'Continue tour' : 'Show me why'}
        </button>
      ) : null}
      <div className="tour-callout-meta">
        <span className="tour-step-count">
          {stepIndex + 1} / {stepCount}
        </span>
        <div className="tour-callout-actions">
          <button type="button" className="tour-btn ghost" onClick={onBack} disabled={stepIndex === 0}>
            Back
          </button>
          <button type="button" className="tour-btn ghost" onClick={onPause}>
            Pause
          </button>
          <button type="button" className="tour-btn ghost" onClick={onSkip}>
            Skip tour
          </button>
          <button type="button" className="tour-btn primary" onClick={onNext} disabled={!canNext}>
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
