import { useGhostStore } from '../../state/store';
import type { AppMode } from '../../state/types';

const MODES: { id: AppMode; label: string }[] = [
  { id: 'multiverse', label: 'WORLD' },
  { id: 'execution', label: 'EXECUTE' },
  { id: 'evidence', label: 'EVIDENCE' },
];

export function ModeDock() {
  const mode = useGhostStore((s) => s.mode);
  const setMode = useGhostStore((s) => s.setMode);

  return (
    <nav className="mode-dock" aria-label="Navigation modes">
      {MODES.map((m) => (
        <button
          key={m.id}
          type="button"
          className={mode === m.id ? 'mode active' : 'mode'}
          onClick={() => setMode(m.id)}
        >
          <span className="glyph">{mode === m.id ? '╔══╗' : '────'}</span>
          <span className="mode-label">{m.label}</span>
        </button>
      ))}
    </nav>
  );
}
