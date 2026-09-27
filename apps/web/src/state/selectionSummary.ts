import type { GhostState, Selection } from './types';

export function buildSelectionSummary(state: GhostState, selection: Selection | null): string {
  if (!selection) return '';
  switch (selection.kind) {
    case 'world': {
      const w = state.worlds[selection.id];
      if (!w) return '';
      const workers = Object.values(state.workers).filter((x) => x.world_id === selection.id).length;
      const arts = Object.values(state.artifacts).filter((x) => x.world_id === selection.id).length;
      return `Selected ${w.label}, status ${w.status}, ${workers} compute resources, ${arts} evidence artifacts.`;
    }
    case 'asset': {
      const a = state.assets[selection.id];
      return a ? `Selected ${a.hostname}, role ${a.role}.` : '';
    }
    case 'task': {
      const t = state.tasks[selection.id];
      return t ? `Selected task ${t.label ?? t.id}, status ${t.status}.` : '';
    }
    case 'worker': {
      const w = state.workers[selection.id];
      return w ? `Selected compute ${w.id}, status ${w.status}, class ${w.resource_class}.` : '';
    }
    case 'artifact':
      return `Selected evidence artifact ${selection.id.slice(-6)}.`;
    case 'claim': {
      const c = state.claims[selection.id];
      return c ? `Selected claim, ${c.verified ? 'verified' : 'unverified'}.` : '';
    }
    case 'attack':
      return `Selected attack path, world ${selection.worldId.slice(0, 8)}.`;
    case 'decision': {
      const d = state.decisions[selection.id];
      return d ? `Selected scheduler decision for task ${d.task_id.slice(0, 8)}.` : '';
    }
    case 'agent':
      return `Selected agent ${selection.id.slice(0, 8)}.`;
    default:
      return '';
  }
}
