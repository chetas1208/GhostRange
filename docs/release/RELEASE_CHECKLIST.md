# GhostRange Release Checklist

**Update (2026-09-27, later same day):** the external-gate items "Run one authorized, bounded CPU worker lifecycle from an ACL-allowed origin" and "Verify provider absence and `owned_workers == []`" below have since been completed (see `docs/milestones/M2_CHECKPOINT_2026-09-27.md`, `docs/milestones/M20_FINAL.md`) — checkboxes not retro-edited below to preserve the point-in-time record, but treat those two as DONE. The golden-campaign-triggered live worker (one integrated run) still has not completed, so the release rule and `RESEARCH_PROTOTYPE` / `NO-SHIP` label below still apply.
## Local gates

- [x] `make demo`
- [x] `bash scripts/m20-release-check.sh`
- [x] Python test matrix: 492 passed, 9 skipped
- [x] Frontend tests: 26 passed
- [x] Frontend typecheck
- [x] M20 mock campaign
- [x] Arena simulated qualification
- [x] Secret-pattern scan of repository content
- [x] README internal-link and Mermaid checks
- [x] Generated browser output ignored
- [x] Public repository created: `chetas1208/GhostRange`
- [x] Reviewed initial commit pushed to `main`

## External gates

- [ ] Deploy current checkout to the control VM
- [ ] Verify current routes and dependencies on the deployed revision
- [ ] Run one authorized, bounded CPU worker lifecycle from an ACL-allowed origin
- [ ] Verify provider absence and `owned_workers == []`
- [ ] Complete screenshot/tour human review
- [ ] Supply target GitHub repository and review remote history
- [x] Stage-only secret/hygiene audit
- [x] Publish without force-push or unauthorized Actions

## Release rule

Until all required external gates are complete, the release label remains `RESEARCH_PROTOTYPE` / `NO-SHIP`.
