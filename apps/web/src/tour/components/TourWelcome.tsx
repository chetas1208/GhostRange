import { useTourStore } from '../tourStore';

export function TourWelcome() {
  const show = useTourStore((s) => s.showWelcome);
  const startTour = useTourStore((s) => s.startTour);
  const dismiss = useTourStore((s) => s.dismissWelcomeExplore);

  if (!show) return null;

  return (
    <div
      className="tour-welcome"
      role="dialog"
      aria-modal="true"
      aria-labelledby="tour-welcome-title"
    >
      <div className="tour-welcome-panel">
        <p className="tour-kicker">GHOSTRANGE</p>
        <h1 id="tour-welcome-title">Investigate systems by building disposable worlds</h1>
        <p className="tour-welcome-lede">
          Run controlled experiments, preserve evidence, and reconstruct what the system knew at
          each moment—not a chat prompt over your infrastructure.
        </p>
        <div className="tour-welcome-actions">
          <button type="button" className="tour-btn primary" onClick={() => startTour('guided')}>
            Take the 4-minute tour
          </button>
          <button type="button" className="tour-btn ghost" onClick={() => dismiss()}>
            Explore on my own
          </button>
        </div>
      </div>
    </div>
  );
}
