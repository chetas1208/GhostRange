import { useTourStore } from '../tourStore';
import { loadTourControlledReplay } from '../tourReplay';
import { applyTourStep } from '../applyTourStep';
import { stepsForVariant } from '../steps/guidedSteps';

const REPO = 'github.com/example/acme-auth';
const INCIDENT =
  'Users retain privileged access after role revocation and token refresh.';
const EVIDENCE = '3 log bundles · 1 request trace · 1 alert';

export function TourInputPanel() {
  const show = useTourStore((s) => s.showInput && s.status === 'RUNNING');
  const step = useTourStore((s) => s.currentStep());
  const markInteraction = useTourStore((s) => s.markInteraction);
  const finishInput = useTourStore((s) => s.finishInputChapter);
  if (!show) return null;

  const build = async () => {
    markInteraction('build-investigation');
    finishInput();
    await loadTourControlledReplay();
    const variant = useTourStore.getState().variant;
    const all = stepsForVariant(variant);
    const twinIdx = all.findIndex((s) => s.id === 'living-twin');
    if (twinIdx >= 0) {
      useTourStore.setState({ stepIndex: twinIdx });
      await applyTourStep(all[twinIdx], { firstScene: true });
    }
  };

  return (
    <div className="tour-input-shell">
      <div className="tour-input-panel">
        <p className="tour-kicker">NEW INVESTIGATION</p>
        <dl className="tour-input-fields">
          <div data-tour-anchor="tour-input-repo">
            <dt>Repository</dt>
            <dd>{REPO}</dd>
          </div>
          <div data-tour-anchor="tour-input-incident">
            <dt>Incident</dt>
            <dd>{INCIDENT}</dd>
          </div>
          <div data-tour-anchor="tour-input-evidence">
            <dt>Evidence</dt>
            <dd>{EVIDENCE}</dd>
          </div>
          <div>
            <dt>Constraints</dt>
            <dd>Max temporary workers 2 · Max spend $1.00 · Production changes disabled</dd>
          </div>
        </dl>
        {step?.interaction === 'build-investigation' ? (
          <button type="button" className="tour-btn primary" data-testid="tour-build" onClick={() => void build()}>
            Build investigation
          </button>
        ) : null}
      </div>
    </div>
  );
}
