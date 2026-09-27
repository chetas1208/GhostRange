import { chapterProgress } from '../steps/guidedSteps';
import type { TourStepV1 } from '../types';

const LABELS: Record<TourStepV1['chapter'], string> = {
  INPUT: 'INPUT',
  UNDERSTAND: 'TWIN',
  INVESTIGATE: 'INVESTIGATE',
  EXECUTE: 'EXECUTE',
  VERIFY: 'VERIFY',
  CONTROL: 'CONTROL',
  PROVE: 'PROVE',
};

export function TourProgress({ chapter }: { chapter: TourStepV1['chapter'] }) {
  const items = chapterProgress(chapter);
  return (
    <nav className="tour-progress" aria-label="Tour chapters">
      {items.map((c) => (
        <span key={c.id} className={c.done ? 'done' : c.active ? 'active' : ''}>
          {LABELS[c.id]}
        </span>
      ))}
    </nav>
  );
}
