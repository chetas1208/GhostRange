import { useGhostStore } from '../../../state/store';
import { useTourStore } from '../../../tour/tourStore';

export function ProductIdentity() {
  const range = useGhostStore((s) => s.range);
  const resetToMultiverseOverview = useGhostStore((s) => s.resetToMultiverseOverview);
  const startTour = useTourStore((s) => s.startTour);

  return (
    <header className="hud top-left">
      <button
        type="button"
        className="identity-button"
        aria-label="GhostRange home — return to Multiverse overview"
        onClick={() => resetToMultiverseOverview()}
      >
        <span className="brand-mark" aria-hidden />
        <div>
          <div className="brand">GHOSTRANGE</div>
          <div className="sub campaign-context">{range?.label ?? range?.slug ?? 'no active campaign'}</div>
        </div>
      </button>
      <button
        type="button"
        className="tour-help-btn"
        aria-label="Take GhostRange product tour"
        onClick={() => startTour('guided')}
      >
        Tour
      </button>
    </header>
  );
}
