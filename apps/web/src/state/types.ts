/** Hand-written mirrors of packages/contracts (M1). */

export type Id = string;

export type AppMode = 'multiverse' | 'execution' | 'evidence';

export type DataSourceMode = 'fixture' | 'live';

export type ConnectionStatus = 'LIVE' | 'FIXTURE' | 'DISCONNECTED' | 'REPLAY';

export type ProviderKind = 'mock' | 'vultr' | 'local_mock' | null;

export type CameraLevel = 'multiverse' | 'world' | 'network' | 'host' | 'execution';

export type WorldStatus =
  | 'REQUESTED'
  | 'PROVISIONING'
  | 'BOOTING'
  | 'READY'
  | 'EXECUTING'
  | 'VERIFYING'
  | 'VERIFIED'
  | 'DESTROYING'
  | 'DESTROYED'
  | 'FAILED';

export type VerificationRingUi = 'pending' | 'running' | 'passed' | 'failed';

export type TaskStatus =
  | 'QUEUED'
  | 'SCHEDULED'
  | 'RUNNING'
  | 'SPECULATED'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED';

export type ResourceClass =
  | 'CPU_SMALL'
  | 'CPU_MEDIUM'
  | 'CPU_LARGE'
  | 'GPU_SMALL'
  | 'GPU_LARGE';

export type ComputeWorkerStatus =
  | 'REQUESTED'
  | 'PROVISIONING'
  | 'BOOTING'
  | 'READY'
  | 'BUSY'
  | 'DRAINING'
  | 'DESTROYING'
  | 'RELEASED'
  | 'FAILED';

export type AgentType = 'INVESTIGATOR' | 'REMEDIATOR' | 'ADVERSARY' | 'VERIFIER' | 'ORCHESTRATOR';

export type ArtifactType =
  | 'LOG'
  | 'PCAP'
  | 'SCREENSHOT'
  | 'MEMORY_DUMP'
  | 'FILE'
  | 'COMMAND_OUTPUT'
  | 'REPORT';

export type ReasonCode =
  | 'DEPENDENCY_CRITICAL'
  | 'HIGH_ASSET_RISK'
  | 'HIGH_UNCERTAINTY'
  | 'CHEAP_INFORMATION_GAIN'
  | 'STRAGGLER_DETECTED'
  | 'GPU_ACCELERATION_EXPECTED'
  | 'GPU_NOT_JUSTIFIED'
  | 'BRANCH_LOW_VALUE'
  | 'BUDGET_EXHAUSTED'
  | 'MARGINAL_GAIN_LOW'
  | 'CPU_SUFFICIENT'
  | 'DEPENDENCY_READY'
  | 'DEPENDENCY_BLOCKED'
  | 'NO_GPU_BENEFIT'
  | 'LOW_PARALLELISM';

export interface RangeV1 {
  id: Id;
  slug: string;
  label: string;
}

export interface WorldV1 {
  id: Id;
  range_id: Id;
  parent_world_id?: Id | null;
  label: string;
  status: WorldStatus;
  failure_reason?: string | null;
  collapsed?: boolean;
  fill?: number;
  /** Shell visible after world.provisioning */
  shell_visible?: boolean;
  /** Topology interactive only after world.ready */
  network_ready?: boolean;
  destroyed?: boolean;
}

export interface WorldForkV1 {
  id: Id;
  parent_world_id: Id;
  child_world_id: Id;
  fork_reason: string;
}

export interface AssetV1 {
  id: Id;
  world_id: Id;
  hostname: string;
  os_family: string;
  role: string;
  ip_address?: string;
  layout?: { x: number; y: number; z: number };
  kind?: 'internet' | 'gateway' | 'vm' | 'service' | 'database' | 'auth';
  fractured?: boolean;
}

export interface NetworkLinkV1 {
  id: Id;
  world_id: Id;
  from_id: Id;
  to_id: Id;
  attack?: boolean;
  faint?: boolean;
}

export interface ComputeWorkerV1 {
  id: Id;
  resource_class: ResourceClass;
  status: ComputeWorkerStatus;
  region: string;
  cost_per_hour_usd: number;
  world_id?: Id | null;
  slot?: number;
  utilization?: number;
  terminating?: boolean;
  provider?: ProviderKind;
  provider_instance_id?: string;
  /** Wireframe only until compute.ready */
  materialized?: boolean;
}

export interface TaskV1 {
  id: Id;
  world_id: Id;
  task_type: string;
  dependencies: Id[];
  status: TaskStatus;
  label?: string;
  priority?: number;
  layout?: { x: number; y: number; z: number };
  speculative_pair_id?: Id;
  winner?: boolean;
  blocked?: boolean;
  evidence_halo?: number;
  stopped_reason?: ReasonCode;
}

export interface SchedulerDecisionV1 {
  id: Id;
  task_id: Id;
  world_id: Id;
  target_resource_class: ResourceClass;
  priority: number;
  estimated_cost_usd: number;
  reason_codes: ReasonCode[];
  notes?: string;
  cpu_runtime_sec?: number;
  gpu_runtime_sec?: number;
}

export interface AgentV1 {
  id: Id;
  world_id: Id;
  agent_type: AgentType;
  asset_id?: Id;
}

export interface ArtifactV1 {
  id: Id;
  world_id: Id;
  artifact_type: ArtifactType;
  content_hash: string;
  command?: string;
  output?: string;
  source_hostname?: string;
  layout?: { x: number; y: number; z: number };
}

export interface ClaimV1 {
  id: Id;
  world_id: Id;
  statement: string;
  anchored: boolean;
  verified: boolean;
}

export interface AttackState {
  world_id: Id;
  path_asset_ids: Id[];
  active: boolean;
}

export interface GhostEvent {
  id: string;
  sequence: number;
  type: string;
  occurred_at: string;
  payload: Record<string, unknown>;
}

export type Selection =
  | { kind: 'asset'; id: Id }
  | { kind: 'world'; id: Id }
  | { kind: 'task'; id: Id }
  | { kind: 'worker'; id: Id }
  | { kind: 'artifact'; id: Id }
  | { kind: 'claim'; id: Id }
  | { kind: 'attack'; id: Id; worldId: Id }
  | { kind: 'decision'; id: Id }
  | { kind: 'agent'; id: Id }
  | { kind: 'cost' };

export interface EventLogEntry {
  id: Id;
  type: string;
  occurred_at: string;
  label: string;
}

export interface GhostWatchSummaryV1 {
  label: string;
  lastStage: string;
  lastOutcome: string;
  campaignState: string;
}

export interface MeshSummaryV1 {
  label: string;
  bStatus: string;
  cStatus: string;
  eQuarantined: boolean;
  bFirstExperiment: string;
}

export interface CausalSummaryV1 {
  label: string;
  cacheBlocks: boolean;
  transportC: string;
  rejectsCTransport: boolean;
}

export interface PromotionSummaryV1 {
  candidateId: Id;
  state: string;
  hash: string;
  blockers: string[];
  evidenceRoot: string;
  patchPreview: string;
  showProductionShadow?: boolean;
}

export interface GhostState {
  range: RangeV1 | null;
  campaignId: Id | null;
  campaignPhase: string | null;
  streamRangeId: Id | null;
  lastEventSeq: number;
  sseStatus: 'idle' | 'connecting' | 'open' | 'reconnecting' | 'closed' | 'failed';
  arenaQualification: string | null;
  dataSource: DataSourceMode;
  streamConnected: boolean;
  activeProvider: ProviderKind;
  worlds: Record<Id, WorldV1>;
  forks: WorldForkV1[];
  assets: Record<Id, AssetV1>;
  links: Record<Id, NetworkLinkV1>;
  workers: Record<Id, ComputeWorkerV1>;
  tasks: Record<Id, TaskV1>;
  decisions: Record<Id, SchedulerDecisionV1>;
  agents: Record<Id, AgentV1>;
  artifacts: Record<Id, ArtifactV1>;
  claims: Record<Id, ClaimV1>;
  attacks: AttackState[];
  processedEventIds: Set<string>;
  /** Live SSE events retained for timeline scrub (no fixture). */
  liveEventBuffer: GhostEvent[];
  /** Workers torn down — late compute.ready must not recreate. */
  releasedWorkerIds: Set<string>;
  sequence: number;
  totalCostUsd: number;
  /** Monotonic bump when cost.snapshot.updated arrives. */
  costRevision: number;
  costSemanticType: string | null;
  costUnknownComponents: string[];
  /** task_id → first/last event timestamps for timing decomposition (partial). */
  taskTiming: Record<
    Id,
    { queued_at?: string; started_at?: string; completed_at?: string; failed_at?: string }
  >;
  /** @deprecated use dataSource + streamConnected */
  live: boolean;
  eventLog: EventLogEntry[];
  mode: AppMode;
  cameraLevel: CameraLevel;
  focusedWorldId: Id | null;
  selection: Selection | null;
  replayTimeMs: number;
  replayMaxMs: number;
  timelineMarkers: { t: number; label: string }[];
  ariaSelectionSummary: string;
  replayScrubbing: boolean;
  hoverTarget: Selection | null;
  streamError: string | null;
  verificationRing: VerificationRingUi;
  cameraDolly: number;
  promotion: PromotionSummaryV1 | null;
  ghostwatch: GhostWatchSummaryV1 | null;
  mesh: MeshSummaryV1 | null;
  causal: CausalSummaryV1 | null;
  authorizationGate: {
    position: [number, number, number];
    state: 'EVALUATING' | 'AUTHORIZED' | 'DENIED' | 'STALE' | 'HUMAN_REQUIRED';
    actionType?: string;
    reason?: string;
  } | null;
}
