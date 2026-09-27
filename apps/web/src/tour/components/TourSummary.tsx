import { useGhostStore } from '../../state/store';
import { selectWorkerCount } from '../../state/selectors';
import { useTourStore } from '../tourStore';

export function TourSummary() {
  const show = useTourStore((s) => s.showSummary);
  const restart = useTourStore((s) => s.restartTour);
  const skip = useTourStore((s) => s.skipTour);
  const workerCount = useGhostStore(selectWorkerCount);
  const cost = useGhostStore((s) => s.totalCostUsd);
  const artifacts = useGhostStore((s) => Object.keys(s.artifacts).length);

  if (!show) return null;

  return (
    <div className="tour-summary" role="dialog" aria-labelledby="tour-summary-title">
      <div className="tour-summary-panel">
        <p className="tour-kicker">GHOSTRANGE</p>
        <h1 id="tour-summary-title">From system to evidence</h1>
        <p className="tour-summary-flow">
          SYSTEM → TWIN → HYPOTHESES → EXPERIMENTS → COMPUTE → CAUSAL EVIDENCE → REMEDIATION →
          AUTHORIZATION → VERIFICATION
        </p>
        <ul className="tour-summary-stats">
          <li>Hypotheses tested: 3</li>
          <li>Refuted: 2</li>
          <li>Remediations tested: 2</li>
          <li>Counterexamples found: 1</li>
          <li>Workers in replay peak: 4</li>
          <li>Final workers: {workerCount}</li>
          <li>Campaign cost (replay): ${cost.toFixed(2)}</li>
          <li>Evidence artifacts: {artifacts}</li>
        </ul>
        <p className="tour-summary-closer">
          GhostRange does not ask an AI what went wrong and trust the answer. It builds worlds, runs
          experiments, tries to disprove its conclusions, and shows you the evidence.
        </p>
        <div className="tour-welcome-actions">
          <button type="button" className="tour-btn primary" onClick={() => skip()}>
            Explore this investigation
          </button>
          <button type="button" className="tour-btn ghost" onClick={() => restart()}>
            Restart tour
          </button>
        </div>
      </div>
    </div>
  );
}
