import { selectHasActiveWorld } from '../../../state/selectors';
import { useGhostStore } from '../../../state/store';
import { useTourStore } from '../../../tour/tourStore';

export function EmptyChamberHint() {
  const hasWorld = useGhostStore(selectHasActiveWorld);
  const mode = useGhostStore((s) => s.mode);
  const tourUi = useTourStore((s) => s.showWelcome || s.isTourSession);

  if (tourUi || hasWorld || mode !== 'multiverse') return null;

  return (
    <p className="empty-chamber-hint" role="note">
      Press <kbd>⌘</kbd>/<kbd>Ctrl</kbd>+<kbd>K</kbd> to create a range
    </p>
  );
}
