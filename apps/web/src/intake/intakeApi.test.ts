import { describe, expect, it } from 'vitest';
import {
  buildIntakePayload,
  isValidIntakeForm,
  narrationFromSummary,
  slugify,
} from './intakeApi';

describe('slugify', () => {
  it('lowercases, hyphenates, and strips punctuation', () => {
    expect(slugify('Privilege persists after role revocation')).toBe(
      'privilege-persists-after-role-revocation',
    );
  });

  it('never returns an empty string', () => {
    expect(slugify('   ')).toBe('incident');
    expect(slugify('!!!')).toBe('incident');
  });
});

describe('buildIntakePayload', () => {
  const baseInput = {
    repositoryUrl: '  https://github.com/acme/auth-service  ',
    branch: '',
    incidentTitle: 'Privilege persists after role revocation',
    incidentDescription: 'A user can still access admin endpoints after their role is revoked.',
  };

  it('matches the minimum input contract shape', () => {
    const fixedNow = () => new Date('2026-09-27T07:30:00.000Z');
    const payload = buildIntakePayload(baseInput, { now: fixedNow, caseSuffix: '20260927073000' });

    expect(payload).toEqual({
      case_id: 'privilege-persists-after-role-revocation-20260927073000',
      incident: {
        title: 'Privilege persists after role revocation',
        description: 'A user can still access admin endpoints after their role is revoked.',
        observed_at: '2026-09-27T07:30:00.000Z',
      },
      system: {
        repository_url: 'https://github.com/acme/auth-service',
        branch: 'main',
      },
      evidence: [],
      constraints: {
        max_workers: 1,
        max_cost_usd: 1.0,
        live_production_actions: false,
      },
    });
  });

  it('defaults a blank branch to main', () => {
    const payload = buildIntakePayload({ ...baseInput, branch: '   ' });
    expect(payload.system.branch).toBe('main');
  });

  it('preserves an explicit non-default branch', () => {
    const payload = buildIntakePayload({ ...baseInput, branch: 'release/2.0' });
    expect(payload.system.branch).toBe('release/2.0');
  });

  it('always sends an empty evidence array (runtime evidence is out of scope for this pass)', () => {
    const payload = buildIntakePayload(baseInput);
    expect(payload.evidence).toEqual([]);
  });
});

describe('narrationFromSummary', () => {
  it('mirrors the backend narration phrasing', () => {
    const lines = narrationFromSummary({
      files_scanned: 47,
      files_relevant: 12,
      services_identified: 5,
      data_stores_identified: 2,
      external_interfaces_identified: 1,
    });

    expect(lines).toEqual([
      'Repository acquired.',
      '12 files relevant of 47 scanned.',
      '5 services identified.',
      '2 data stores identified.',
      '1 external interfaces identified.',
    ]);
  });
});

describe('isValidIntakeForm', () => {
  const valid = {
    repositoryUrl: 'https://github.com/acme/auth-service',
    branch: 'main',
    incidentTitle: 'Title',
    incidentDescription: 'Description',
  };

  it('accepts a fully filled form', () => {
    expect(isValidIntakeForm(valid)).toBe(true);
  });

  it.each(['repositoryUrl', 'incidentTitle', 'incidentDescription'] as const)(
    'rejects a form missing %s',
    (field) => {
      expect(isValidIntakeForm({ ...valid, [field]: '   ' })).toBe(false);
    },
  );

  it('does not require a branch (defaults are applied at submit time)', () => {
    expect(isValidIntakeForm({ ...valid, branch: '' })).toBe(true);
  });
});
