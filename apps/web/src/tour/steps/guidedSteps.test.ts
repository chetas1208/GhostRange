import { describe, expect, it } from 'vitest';
import { GUIDED_TOUR_STEPS, stepsForVariant } from './guidedSteps';

describe('guided tour steps', () => {
  it('includes history chapter for guided variant', () => {
    const ids = stepsForVariant('guided').map((s) => s.id);
    expect(ids).toContain('history');
  });

  it('explore variant has summary only surface steps', () => {
    const explore = stepsForVariant('explore');
    expect(explore.length).toBeGreaterThan(0);
    expect(GUIDED_TOUR_STEPS.some((s) => s.variants.includes('explore'))).toBe(true);
  });
});
