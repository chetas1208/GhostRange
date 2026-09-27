import { useGhostStore } from '../../../state/store';

export function ErrorBanner() {
  const error = useGhostStore((s) => s.streamError);
  if (!error) return null;
  return (
    <div className="error-banner" role="alert">
      {error}
    </div>
  );
}
