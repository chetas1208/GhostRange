/** Visual tokens — near-black chamber, restrained accents. */
export const colors = {
  void: '#0a0a0c',
  graphite: '#141418',
  surface: '#1c1c22',
  link: '#8b95a8',
  linkActive: '#a8b4c8',
  mint: '#6ee7b7',
  electric: '#60a5fa',
  violet: '#a78bfa',
  amber: '#fbbf24',
  failure: '#f87171',
  selection: '#93c5fd',
} as const;

export type SemanticState =
  | 'healthy'
  | 'investigating'
  | 'attack'
  | 'patching'
  | 'verifying'
  | 'failed'
  | 'pruned'
  | 'verified'
  | 'provisioning';

export function accentForState(state: SemanticState): string {
  switch (state) {
    case 'verified':
      return colors.mint;
    case 'verifying':
    case 'provisioning':
      return colors.electric;
    case 'investigating':
      return colors.violet;
    case 'attack':
    case 'failed':
      return colors.failure;
    case 'patching':
      return colors.amber;
    default:
      return colors.link;
  }
}
