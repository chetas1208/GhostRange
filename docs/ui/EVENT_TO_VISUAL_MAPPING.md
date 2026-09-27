# Event → visual mapping (core)

| Event | State change | 3D | DOM | Timeline |
|-------|--------------|-----|-----|----------|
| `world.provisioning` | shell_visible | WorldProvisioningShell | — | marker |
| `world.network_ready` | network_ready | topology nodes appear | — | marker |
| `attack.path_active` | attacks[].active | AttackPath pulse + bloom | — | incident |
| `worker.provisioning` | worker PROVISIONING | ProvisioningGhost shell | — | provision |
| `worker.ready` | worker READY | CpuWorker/GpuWorker solid | inspector | — |
| `worker.released` | worker RELEASED | WorkerTermination dissolve | worker count ↓ | teardown |
| `task.running` | task status | ExecutionTask internal motion | task inspector | — |
| `scheduler.decision` | decisions[id] | SchedulerDecisionMarker | DecisionInspector | — |
| `golden_path.phase` | eventLog | — (phase label in log) | command preview | scrub |
| `campaign.phase` | eventLog | — | campaign label | marker |
| `ghostledger.sealed` | verificationRing progress | VerificationRing | evidence inspector | verify |
| `director.decision` | eventLog | HypothesisBranch emphasis | world inspector | hypothesis |

Full reducer: `apps/web/src/state/eventReducer.ts`. Accessibility: `SelectionAnnouncer` + inspector DOM mirrors selection.
