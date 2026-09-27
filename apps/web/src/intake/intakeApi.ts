/**
 * Pure request-building + narration-formatting logic for the investigation
 * intake screen, kept separate from the React component so it is testable
 * without a DOM (see intakeApi.test.ts).
 *
 * Matches the minimum input contract (see
 * docs/architecture/PRODUCT.md and ghostrange_contracts.investigation_intake
 * on the backend) and the POST /v1/investigations/intake response shape
 * (see apps/api/ghostrange_api/investigation_routes.py).
 */

export interface IntakeFormInput {
  repositoryUrl: string;
  branch: string;
  incidentTitle: string;
  incidentDescription: string;
}

export interface InvestigationIntakePayload {
  case_id: string;
  incident: {
    title: string;
    description: string;
    observed_at: string;
  };
  system: {
    repository_url: string;
    branch: string;
  };
  evidence: unknown[];
  constraints: {
    max_workers: number;
    max_cost_usd: number;
    live_production_actions: boolean;
  };
}

export interface RepoScanSummary {
  files_scanned: number;
  files_relevant: number;
  services_identified: number;
  data_stores_identified: number;
  external_interfaces_identified: number;
}

export interface IntakeResponse {
  case_id: string;
  derived_system_model: {
    summary: RepoScanSummary;
    confidence_disclaimer: string;
    services: Array<{ name: string; inferred_role: string }>;
  };
  narration: string[];
}

/** Lowercase, hyphenated, alphanumeric-only slug — never returns an empty
 * string ('incident' is the fallback so a blank title still yields a
 * usable case_id). */
export function slugify(text: string): string {
  const slug = text
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return slug || 'incident';
}

export interface BuildIntakePayloadOptions {
  now?: () => Date;
  /** Override the auto-generated timestamp suffix on case_id (for deterministic tests). */
  caseSuffix?: string;
}

export function buildIntakePayload(
  input: IntakeFormInput,
  options: BuildIntakePayloadOptions = {},
): InvestigationIntakePayload {
  const now = options.now ?? (() => new Date());
  const observedAt = now().toISOString();
  const suffix = options.caseSuffix ?? observedAt.replace(/[^0-9]/g, '').slice(0, 14);

  return {
    case_id: `${slugify(input.incidentTitle)}-${suffix}`,
    incident: {
      title: input.incidentTitle.trim(),
      description: input.incidentDescription.trim(),
      observed_at: observedAt,
    },
    system: {
      repository_url: input.repositoryUrl.trim(),
      branch: input.branch.trim() || 'main',
    },
    evidence: [],
    constraints: {
      max_workers: 1,
      max_cost_usd: 1.0,
      live_production_actions: false,
    },
  };
}

/** Client-side fallback narration formatter, mirroring
 * RepoScanSummaryV1.narration() / investigation_routes._narration_lines on
 * the backend — used only if a response is ever missing its `narration`
 * field. Kept in sync deliberately; if the backend's phrasing changes,
 * update both. */
export function narrationFromSummary(summary: RepoScanSummary): string[] {
  return [
    'Repository acquired.',
    `${summary.files_relevant} files relevant of ${summary.files_scanned} scanned.`,
    `${summary.services_identified} services identified.`,
    `${summary.data_stores_identified} data stores identified.`,
    `${summary.external_interfaces_identified} external interfaces identified.`,
  ];
}

export function isValidIntakeForm(input: IntakeFormInput): boolean {
  return (
    input.repositoryUrl.trim().length > 0 &&
    input.incidentTitle.trim().length > 0 &&
    input.incidentDescription.trim().length > 0
  );
}
