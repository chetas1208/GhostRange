import { useState } from 'react';
import type { FormEvent } from 'react';
import { API_BASE } from '../config/apiBase';
import {
  buildIntakePayload,
  isValidIntakeForm,
  narrationFromSummary,
  type IntakeFormInput,
  type IntakeResponse,
} from './intakeApi';
import './intake.css';

type Phase = 'form' | 'submitting' | 'narrating' | 'error';

export interface InvestigationIntakeScreenProps {
  /** Called when the person clicks through after seeing the narration.
   * This screen intentionally does not itself materialize the derived
   * model into the 3D Multiverse view — that integration is a separate
   * follow-up task (see README in packages/range-compiler/intake). */
  onContinue: () => void;
}

const EMPTY_FORM: IntakeFormInput = {
  repositoryUrl: '',
  branch: 'main',
  incidentTitle: '',
  incidentDescription: '',
};

export function InvestigationIntakeScreen({ onContinue }: InvestigationIntakeScreenProps) {
  const [form, setForm] = useState<IntakeFormInput>(EMPTY_FORM);
  const [phase, setPhase] = useState<Phase>('form');
  const [narration, setNarration] = useState<string[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const canSubmit = isValidIntakeForm(form) && phase !== 'submitting';

  function updateField<K extends keyof IntakeFormInput>(key: K, value: IntakeFormInput[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!isValidIntakeForm(form)) return;

    setPhase('submitting');
    setErrorMessage(null);
    try {
      const payload = buildIntakePayload(form);
      const res = await fetch(`${API_BASE}/v1/investigations/intake`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}) as Record<string, unknown>);
        const detail = typeof body.detail === 'string' ? body.detail : `Request failed (${res.status})`;
        throw new Error(detail);
      }
      const body: IntakeResponse = await res.json();
      const lines = body.narration?.length
        ? body.narration
        : narrationFromSummary(body.derived_system_model.summary);
      setNarration(lines);
      setPhase('narrating');
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Something went wrong reaching GhostRange.');
      setPhase('error');
    }
  }

  return (
    <div className="gr-intake-screen">
      <div className="gr-intake-panel">
        <div className="gr-intake-brand">GHOSTRANGE</div>
        <h1 className="gr-intake-title">Start an investigation</h1>
        <p className="gr-intake-sub">
          Point GhostRange at a public repository and describe the incident. It will derive a
          candidate system model — services, dependencies, external interfaces — before anything
          is built or provisioned.
        </p>

        {phase !== 'narrating' && (
          <form className="gr-intake-form" onSubmit={handleSubmit}>
            <label className="gr-intake-field">
              <span>Repository URL</span>
              <input
                type="url"
                name="repositoryUrl"
                placeholder="https://github.com/acme/auth-service"
                value={form.repositoryUrl}
                onChange={(e) => updateField('repositoryUrl', e.target.value)}
                required
              />
            </label>

            <label className="gr-intake-field gr-intake-field-branch">
              <span>Branch</span>
              <input
                type="text"
                name="branch"
                placeholder="main"
                value={form.branch}
                onChange={(e) => updateField('branch', e.target.value)}
              />
            </label>

            <label className="gr-intake-field">
              <span>Incident title</span>
              <input
                type="text"
                name="incidentTitle"
                placeholder="Privilege persists after role revocation"
                value={form.incidentTitle}
                onChange={(e) => updateField('incidentTitle', e.target.value)}
                required
              />
            </label>

            <label className="gr-intake-field">
              <span>Incident description</span>
              <textarea
                name="incidentDescription"
                rows={4}
                placeholder="A user can still access admin endpoints after their role is revoked."
                value={form.incidentDescription}
                onChange={(e) => updateField('incidentDescription', e.target.value)}
                required
              />
            </label>

            {phase === 'error' && errorMessage && (
              <div className="gr-intake-error" role="alert">
                {errorMessage}
              </div>
            )}

            <button type="submit" className="gr-intake-submit" disabled={!canSubmit}>
              {phase === 'submitting' ? 'Building investigation…' : 'Build Investigation'}
            </button>
          </form>
        )}

        {phase === 'narrating' && (
          <div className="gr-intake-narration" aria-live="polite">
            <ul>
              {narration.map((line, index) => (
                <li key={`${index}-${line}`} style={{ animationDelay: `${index * 0.15}s` }}>
                  {line}
                </li>
              ))}
            </ul>
            <button type="button" className="gr-intake-submit" onClick={onContinue}>
              Continue
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
