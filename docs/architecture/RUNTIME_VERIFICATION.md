# Runtime verification & behavioral contracts

| Component | May | Must not |
|-----------|-----|----------|
| GhostDirector | Propose experiments | Provision compute; authorize production |
| GhostScheduler | Propose placements | Bypass GhostShield; set hard budget |
| Worker | Execute leased task | Call Vultr; access other campaigns |
| GhostWatch | Observe | Control production without permit |
| GhostMesh remote | Influence priors | Become local verified claim; invoke execution |

`GhostRuntimeMonitor` is the hook for trace/temporal properties not discharged by TLA+ or pre-action policy.
