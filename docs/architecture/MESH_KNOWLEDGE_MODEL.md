# Mesh Knowledge Model

## Classes (KnowledgeClassV1)

Counterexample, remediation, verification/experiment templates, search/scheduler priors, failure/rollback/surprise patterns, fidelity lessons.

## Lifecycle

```
LOCAL EVIDENCE → extract → privacy transform → publish → receive → applicability → Director prior → local experiment → local claim
```

## RemoteKnowledgeStatusV1

Never becomes ClaimV1 CURRENT without local evidence.

## Disclosure default

`PRIVATE_LOCAL` until operator enables sharing in policy YAML.
