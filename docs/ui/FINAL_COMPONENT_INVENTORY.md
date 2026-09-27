# Final 3D component inventory

Implementations primarily in `packages/ui-3d/src/` with scene composition in `apps/web/src/ui/scenes/`.

| Component | Mode | File |
|-----------|------|------|
| ReferenceGrid, PerformanceGovernor | env | ui-3d/canvas |
| DepthFog | env | apps/web/components/three/environment |
| RangeWorld, WorldBoundary, WorldFork | multiverse | ui-3d/world |
| HypothesisBranch, WorldCollapse | multiverse | ui-3d/world |
| ServiceNode, DatabaseNode, GatewayNode, AuthNode | multiverse | ui-3d/network |
| AttackPath, NetworkLink | multiverse | ui-3d/network |
| ExecutionTask, DependencyEdge, CriticalPath (via scheduler) | execution | ui-3d/scheduler |
| CpuWorker, GpuWorker, ProvisioningGhost, WorkerTermination | execution | ui-3d/compute |
| SchedulerDecisionMarker, SpeculativeSplit | execution | ui-3d/scheduler |
| ActionGate, ActionPermit, InvariantBoundary | execution | ui-3d/shield |
| ClaimNode, EvidenceArtifact, VerificationRing | evidence | ui-3d/evidence |
| SealedRange, QualificationGate, ArenaRun | evidence | ui-3d/arena |
| EvolutionMarker, ChampionPolicy, ChallengerPolicy | evidence | ui-3d/evolve |

**Rule:** no `MegaScene.tsx`. Scenes only compose; geometry lives in named components.

Detailed per-component fields: extend this doc as components gain new props — each entry should record PURPOSE, INPUT STATE, INTERACTION, REDUCED MOTION (M20 baseline table above).
