import { useGhostStore } from '../../../state/store';

export function SelectionAnnouncer() {
  const message = useGhostStore((s) => s.ariaSelectionSummary);
  return (
    <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">
      {message}
    </div>
  );
}
