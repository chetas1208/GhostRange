import type { ReactNode } from 'react';

/** Placeholder group for replay-driven scene mutations (parent applies clock). */
export function ReplayController({ children }: { children: ReactNode }) {
  return <group>{children}</group>;
}
