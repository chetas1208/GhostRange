# Evolution data poisoning

Threats: fake success runs, tampered cost, poisoned Mesh priors, duplicate rows, outliers.

Controls v1:

- `provenance_digest` required for `ELIGIBLE`
- `tags: poisoned` → `QUARANTINED`
- `FIXTURE` provenance → quarantine
- Holdout manifests must not appear in training manifest digest (process gate — automate in M19)

Red team: `test_poisoned_experience_quarantined`.
