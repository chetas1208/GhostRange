import type { AppMode } from '../../../state/types';
import { useGhostStore } from '../../../state/store';

const MODES: { id: AppMode; label: string; shortcut: string }[] = [
  { id: 'multiverse', label: 'MULTIVERSE', shortcut: '1' },
  { id: 'execution', label: 'EXECUTION', shortcut: '2' },
  { id: 'evidence', label: 'EVIDENCE', shortcut: '3' },
];

export function ModeSelector() {
  const mode = useGhostStore((s) => s.mode);
  const setMode = useGhostStore((s) => s.setMode);

  return (
    <nav className="hud top-center mode-selector" aria-label="Primary modes">
      {MODES.map((m) => (
        <button
          key={m.id}
          type="button"
          className={mode === m.id ? 'mode-pill active' : 'mode-pill'}
          aria-current={mode === m.id ? 'page' : undefined}
          aria-keyshortcuts={m.shortcut}
          onClick={() => setMode(m.id)}
        >
          <span className="mode-glyph" aria-hidden>
            {mode === m.id ? '▣' : '▢'}
          </span>
          {m.label}
        </button>
      ))}
    </nav>
  );
}
