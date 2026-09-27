export type ResourceClass =
  | 'CPU_SMALL'
  | 'CPU_MEDIUM'
  | 'CPU_LARGE'
  | 'GPU_SMALL'
  | 'GPU_LARGE';

export type ComputeStatus =
  | 'REQUESTED'
  | 'PROVISIONING'
  | 'BOOTING'
  | 'READY'
  | 'BUSY'
  | 'DRAINING'
  | 'DESTROYING'
  | 'RELEASED'
  | 'FAILED';

export type WorldLifecycleStatus =
  | 'REQUESTED'
  | 'PROVISIONING'
  | 'BOOTING'
  | 'READY'
  | 'EXECUTING'
  | 'VERIFYING'
  | 'VERIFIED'
  | 'FAILED'
  | 'PRUNED'
  | 'DESTROYING'
  | 'DESTROYED';

export type TaskStatus =
  | 'CREATED'
  | 'QUEUED'
  | 'BLOCKED'
  | 'SCHEDULED'
  | 'RUNNING'
  | 'SPECULATED'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED';

export type NodeStatus =
  | 'healthy'
  | 'investigating'
  | 'under_attack'
  | 'compromised'
  | 'patching'
  | 'verifying'
  | 'failed';

export type LinkStatus = 'idle' | 'active' | 'attack' | 'faint' | 'disabled';

export type AttackPathState = 'planned' | 'active' | 'succeeded' | 'blocked' | 'historical';

export type ClaimState = 'unsupported' | 'partial' | 'verified' | 'contradicted' | 'superseded';

export type VerificationRingState = 'pending' | 'running' | 'passed' | 'failed';

export type AgentType = 'INVESTIGATOR' | 'REMEDIATOR' | 'ADVERSARY' | 'VERIFIER' | 'ORCHESTRATOR';

export type ArtifactType =
  | 'LOG'
  | 'PCAP'
  | 'SCREENSHOT'
  | 'MEMORY_DUMP'
  | 'FILE'
  | 'COMMAND_OUTPUT'
  | 'REPORT'
  | 'HTTP_REQUEST'
  | 'HTTP_RESPONSE';

export type NetworkNodeKind =
  | 'internet'
  | 'gateway'
  | 'vm'
  | 'container'
  | 'service'
  | 'database'
  | 'auth'
  | 'gpu'
  | 'compute_mapped'
  | 'generic';

export type DependencyState = 'unresolved' | 'ready' | 'fulfilled' | 'failed';

export type InteractionState = 'idle' | 'hovered' | 'focused' | 'selected' | 'disabled' | 'stale' | 'error';
