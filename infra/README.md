# infra/

Owner: Agent 03 (Infrastructure / Range Provisioning), per
`docs/milestones/M2_COORDINATION.md`. This directory is for **generic, range-agnostic**
provisioning tooling — anything that would be shared across multiple ranges, as
opposed to `ranges/<name>/` (one range's own spec + topology + compose files) or
`packages/range-iac/` (the compiler code itself).

## Why this directory is currently near-empty

`Decisions.md` item 7 locked **OpenTofu + cloud-init** as the project's IaC approach.
This M2 deliverable's actual RangeSpec-to-Vultr compiler
(`packages/range-iac/ghostrange_range_iac/compiler.py`) instead produces **direct
Vultr API request objects** (consumed by `apply.py` against a `VultrProviderProtocol`
— see that package's README) rather than generated OpenTofu HCL.

This is a deliberate, recorded scope decision, not a silent divergence — see
`docs/adr/ADR-M2-RANGE-PROVISIONING.md`'s "OpenTofu HCL generation vs. direct
provider-call compilation" section for the full reasoning (short version: ADR-006
already commits to `packages/vultr-control` being the *single* choke point for all
Vultr API calls; a generated Terraform/OpenTofu config using the Vultr provider would
be a second, competing path to Vultr credentials that bypasses that choke point
entirely, and GhostScheduler's create/destroy/fork pattern for disposable worlds is
driven by code, not by a human running `tofu apply`, so Terraform's declarative-diff
model buys less here than it would for genuinely long-lived, hand-managed
infrastructure).

If a future milestone finds a real need for OpenTofu specifically (e.g. hand-managed,
long-lived infrastructure that benefits from plan/diff review — most plausibly the
orchestration/worker fleet itself, not range assets, per ADR-006 §VKE discussion),
this is where that configuration would live. Nothing here should be built ahead of
that actual need.

## What is actually here

Nothing yet beyond this README. All real, working provisioning artifacts for M2 live
in `packages/range-iac/` (the compiler) and `ranges/ghostrange-auth-lab-v1/` (the one
canonical range's spec, topology, and cloud-init/docker-compose content) — see both
READMEs and `docs/adr/ADR-M2-RANGE-PROVISIONING.md`.
