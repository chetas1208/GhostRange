# GhostRange Release Checklist

## Local gates

- [x] `make demo`
- [x] `bash scripts/m20-release-check.sh`
- [x] Python test matrix: 491 passed, 9 skipped
- [x] Frontend tests: 26 passed
- [x] Frontend typecheck
- [x] M20 mock campaign
- [x] Arena simulated qualification
- [x] Secret-pattern scan of repository content
- [x] README internal-link and Mermaid checks
- [x] Generated browser output ignored

## External gates

- [ ] Deploy current checkout to the control VM
- [ ] Verify current routes and dependencies on the deployed revision
- [ ] Run one authorized, bounded CPU worker lifecycle from an ACL-allowed origin
- [ ] Verify provider absence and `owned_workers == []`
- [ ] Complete screenshot/tour human review
- [ ] Supply target GitHub repository and review remote history
- [ ] Stage-only secret/hygiene audit
- [ ] Publish without force-push or unauthorized Actions

## Release rule

Until all required external gates are complete, the release label remains `RESEARCH_PROTOTYPE` / `NO-SHIP`.

