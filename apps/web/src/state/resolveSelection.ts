import type { AppMode, GhostState, Selection } from './types';

export type SelectionSpace = 'multiverse' | 'execution' | 'evidence';

export function resolveSelection(
  _space: SelectionSpace,
  kind: Selection['kind'],
  id: string,
  extra?: Partial<{ worldId: string }>,
): Selection {
  switch (kind) {
    case 'attack':
      return { kind: 'attack', id, worldId: extra?.worldId ?? id };
    default:
      return { kind, id } as Selection;
  }
}

export function clearSelectionForMode(state: GhostState, mode: AppMode): Selection | null {
  if (!state.selection) return null;
  const k = state.selection.kind;
  if (mode === 'multiverse' && (k === 'world' || k === 'asset' || k === 'attack')) return null;
  if (mode === 'execution' && (k === 'task' || k === 'worker' || k === 'decision')) return null;
  if (mode === 'evidence' && (k === 'artifact' || k === 'claim')) return null;
  return state.selection;
}
