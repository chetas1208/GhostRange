# M10 Security Review (draft)

## Scope

GhostRange API, golden path, Director/adversarial safety validators, Caldera adapter URL policy.

## Findings (initial)

| ID | Severity | Finding | Status |
|----|----------|---------|--------|
| S1 | info | Live provisioning requires explicit `GHOSTRANGE_LIVE` | mitigated |
| S2 | info | Caldera client rejects non-range-local base URLs | tested |
| S3 | info | Adversarial search rejects external IPs in candidates | tested |
| S4 | open | Full SSRF audit on API import paths not complete | backlog |
| S5 | open | Cross-world network isolation not live-tested | backlog |

## Unresolved risks

- Model prompt injection via range service responses (policy: treat as data)
- Production deployment boundary relies on human process, not tool enforcement

Agent 37 full matrix: pending chaos campaign.
