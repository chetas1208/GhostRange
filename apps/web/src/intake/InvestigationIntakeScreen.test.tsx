import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { InvestigationIntakeScreen } from './InvestigationIntakeScreen';

// No @testing-library/react is set up in this project yet (see apps/web
// package.json) and this task shouldn't introduce a new frontend test
// framework just for one screen. renderToStaticMarkup is part of
// react-dom (already a dependency) and needs no DOM, so it's enough for a
// basic "does this component render the right static markup" smoke test.

describe('InvestigationIntakeScreen', () => {
  it('renders the intake form with the four required inputs and the submit button', () => {
    const html = renderToStaticMarkup(<InvestigationIntakeScreen onContinue={() => {}} />);

    expect(html).toContain('GHOSTRANGE');
    expect(html).toContain('Start an investigation');
    expect(html).toContain('name="repositoryUrl"');
    expect(html).toContain('name="branch"');
    expect(html).toContain('name="incidentTitle"');
    expect(html).toContain('name="incidentDescription"');
    expect(html).toContain('Build Investigation');
  });

  it('defaults the branch field to "main"', () => {
    const html = renderToStaticMarkup(<InvestigationIntakeScreen onContinue={() => {}} />);
    expect(html).toContain('value="main"');
  });

  it('does not render the narration list before any submission', () => {
    const html = renderToStaticMarkup(<InvestigationIntakeScreen onContinue={() => {}} />);
    expect(html).not.toContain('gr-intake-narration');
  });
});
