"""Shared enumerations used across GhostRange contract models.

These are the machine-readable vocabularies domain objects are built from.
Keeping them in one module avoids the same concept (e.g. "how risky is this
asset") being independently invented with different spellings in
range-runtime, scheduler, and evidence.
"""

from __future__ import annotations

from enum import Enum


class RangeLifecycleState(str, Enum):
    """Authoritative Range state machine.

    This reconciles the two views handed down from the product spec (a
    linear happy-path list, and an implicit "things can fail/stop early"
    view) into one machine: FAILED is reachable from every non-terminal
    state, STOPPING/DESTROYING form an explicit teardown path distinct from
    a hard failure, and DESTROYED/FAILED are the only terminal states.
    See ``RANGE_LIFECYCLE_TRANSITIONS`` in ``range.py`` for the transition
    table this enum backs.
    """

    REQUESTED = "REQUESTED"
    PLANNING = "PLANNING"
    PROVISIONING = "PROVISIONING"
    BOOTING = "BOOTING"
    READY = "READY"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    STOPPING = "STOPPING"
    DESTROYING = "DESTROYING"
    DESTROYED = "DESTROYED"
    FAILED = "FAILED"


class WorldStatus(str, Enum):
    """Lifecycle of an individual World (a forked branch inside a Range)."""

    REQUESTED = "REQUESTED"
    PROVISIONING = "PROVISIONING"
    READY = "READY"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    DESTROYED = "DESTROYED"
    FAILED = "FAILED"


class SecurityCriticality(str, Enum):
    """How much damage compromise/misconfiguration of a thing would cause."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ResourceClass(str, Enum):
    """Coarse compute sizing classes GhostScheduler allocates against.

    Shared between ``ResourceProfileV1`` (what a task asks for) and
    ``SchedulerDecisionV1.target_resource_class`` (what got allocated),
    and mirrored by ``ComputeWorkerV1.resource_class`` for the actual
    provisioned worker.
    """

    CPU_SMALL = "CPU_SMALL"
    CPU_MEDIUM = "CPU_MEDIUM"
    CPU_LARGE = "CPU_LARGE"
    GPU_SMALL = "GPU_SMALL"
    GPU_LARGE = "GPU_LARGE"


class ComputeProvider(str, Enum):
    VULTR = "VULTR"
    LOCAL_MOCK = "LOCAL_MOCK"


class ComputeWorkerStatus(str, Enum):
    REQUESTED = "REQUESTED"
    PROVISIONING = "PROVISIONING"
    READY = "READY"
    BUSY = "BUSY"
    RELEASED = "RELEASED"
    FAILED = "FAILED"


class TaskType(str, Enum):
    INVESTIGATE = "INVESTIGATE"
    REMEDIATE = "REMEDIATE"
    ATTACK = "ATTACK"
    VERIFY = "VERIFY"
    PROVISION = "PROVISION"
    TEARDOWN = "TEARDOWN"
    ANALYZE = "ANALYZE"


class TaskStatus(str, Enum):
    QUEUED = "QUEUED"
    SCHEDULED = "SCHEDULED"
    RUNNING = "RUNNING"
    SPECULATED = "SPECULATED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AgentType(str, Enum):
    INVESTIGATOR = "INVESTIGATOR"
    REMEDIATOR = "REMEDIATOR"
    ADVERSARY = "ADVERSARY"
    VERIFIER = "VERIFIER"
    ORCHESTRATOR = "ORCHESTRATOR"


class AgentStatus(str, Enum):
    STARTED = "STARTED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ReasonCode(str, Enum):
    """Machine-readable justification codes attached to a SchedulerDecision.

    These are consumed by the frontend to render *why* the scheduler did
    something (not just what it did), and by evaluation tooling to check
    the scheduler is making decisions for the reasons it claims. Fixed
    vocabulary, no free-text reason may substitute for these on the
    decision itself (``reason_codes``); free text belongs in
    ``SchedulerDecisionV1.notes`` if ever needed.
    """

    DEPENDENCY_CRITICAL = "DEPENDENCY_CRITICAL"
    HIGH_ASSET_RISK = "HIGH_ASSET_RISK"
    HIGH_UNCERTAINTY = "HIGH_UNCERTAINTY"
    CHEAP_INFORMATION_GAIN = "CHEAP_INFORMATION_GAIN"
    STRAGGLER_DETECTED = "STRAGGLER_DETECTED"
    GPU_ACCELERATION_EXPECTED = "GPU_ACCELERATION_EXPECTED"
    GPU_NOT_JUSTIFIED = "GPU_NOT_JUSTIFIED"
    BRANCH_LOW_VALUE = "BRANCH_LOW_VALUE"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    MARGINAL_GAIN_LOW = "MARGINAL_GAIN_LOW"
    # M3 branch-aware scheduling (additive)
    BRANCH_HIGH_UNCERTAINTY = "BRANCH_HIGH_UNCERTAINTY"
    BRANCH_HIGH_RISK = "BRANCH_HIGH_RISK"
    BRANCH_VERIFICATION_NEAR_COMPLETE = "BRANCH_VERIFICATION_NEAR_COMPLETE"
    BRANCH_EARLY_FAILURE = "BRANCH_EARLY_FAILURE"
    BRANCH_LOW_EXPECTED_VALUE = "BRANCH_LOW_EXPECTED_VALUE"
    PARALLEL_WORLD_SAFE = "PARALLEL_WORLD_SAFE"
    PARALLEL_TASK_SAFE = "PARALLEL_TASK_SAFE"
    SCALE_OUT_QUEUE_PRESSURE = "SCALE_OUT_QUEUE_PRESSURE"
    SCALE_OUT_CRITICAL_PATH = "SCALE_OUT_CRITICAL_PATH"
    SCALE_IN_IDLE_CAPACITY = "SCALE_IN_IDLE_CAPACITY"
    SPECULATION_STRAGGLER = "SPECULATION_STRAGGLER"
    SPECULATION_HIGH_VALUE_BRANCH = "SPECULATION_HIGH_VALUE_BRANCH"
    PRUNE_REMEDIATION_FAILED = "PRUNE_REMEDIATION_FAILED"
    PRUNE_REGRESSION_FAILED = "PRUNE_REGRESSION_FAILED"
    PRUNE_LOW_VALUE = "PRUNE_LOW_VALUE"
    PRUNE_BUDGET_PRESSURE = "PRUNE_BUDGET_PRESSURE"
    CONTINUE_NEEDS_EVIDENCE = "CONTINUE_NEEDS_EVIDENCE"
    CONTINUE_ALTERNATIVE_PATH_UNTESTED = "CONTINUE_ALTERNATIVE_PATH_UNTESTED"
    STOP_SUFFICIENT_VERIFICATION = "STOP_SUFFICIENT_VERIFICATION"
    STOP_MARGINAL_GAIN_LOW = "STOP_MARGINAL_GAIN_LOW"
    WORLD_TERMINATION_APPROVED = "WORLD_TERMINATION_APPROVED"
    CPU_SUFFICIENT = "CPU_SUFFICIENT"


class HypothesisStatus(str, Enum):
    OPEN = "OPEN"
    SUPPORTED = "SUPPORTED"
    REFUTED = "REFUTED"


class AttackOutcome(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    INCONCLUSIVE = "INCONCLUSIVE"


class VerificationMethod(str, Enum):
    ADVERSARIAL_ATTACK = "ADVERSARIAL_ATTACK"
    STATIC_ANALYSIS = "STATIC_ANALYSIS"
    RE_EXECUTION = "RE_EXECUTION"
    PEER_REVIEW = "PEER_REVIEW"


class VerificationResult(str, Enum):
    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    INCONCLUSIVE = "INCONCLUSIVE"


class ArtifactType(str, Enum):
    LOG = "LOG"
    PCAP = "PCAP"
    SCREENSHOT = "SCREENSHOT"
    MEMORY_DUMP = "MEMORY_DUMP"
    FILE = "FILE"
    COMMAND_OUTPUT = "COMMAND_OUTPUT"
    REPORT = "REPORT"


class HashAlgorithm(str, Enum):
    SHA256 = "SHA256"


class ObservationType(str, Enum):
    FILE_STATE = "FILE_STATE"
    PROCESS_STATE = "PROCESS_STATE"
    NETWORK_TRAFFIC = "NETWORK_TRAFFIC"
    LOG_LINE = "LOG_LINE"
    COMMAND_RESULT = "COMMAND_RESULT"
    AGENT_ASSERTION = "AGENT_ASSERTION"


class ExecutionStatus(str, Enum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"


class AssetRole(str, Enum):
    WORKSTATION = "WORKSTATION"
    SERVER = "SERVER"
    DOMAIN_CONTROLLER = "DOMAIN_CONTROLLER"
    FIREWALL = "FIREWALL"
    DATABASE = "DATABASE"
    LOAD_BALANCER = "LOAD_BALANCER"
    OTHER = "OTHER"


class AbilityCategory(str, Enum):
    """MITRE-tactic-shaped allowlist of *what kind* of action a
    ``RangeOwnershipTokenV1`` authorizes, independent of *which* target.

    This is the ``capabilities`` vocabulary named in
    ``docs/security/EXECUTION_POLICY.md`` §2 and the ``action_category``
    field on ``ExecutionRequestV1`` (``policy.py``) — a fixed, closed
    vocabulary on purpose: a token's capability list is checked with
    ``in``, never with free-text string matching, so there is nothing an
    injected instruction could be "close enough" to.
    """

    RECON = "RECON"
    EXPLOIT = "EXPLOIT"
    PERSISTENCE = "PERSISTENCE"
    EXFIL_SIM = "EXFIL_SIM"
    PROVISION = "PROVISION"
    TEARDOWN = "TEARDOWN"


class PolicyActorKind(str, Enum):
    """Who/what issued a request that reached the policy-check service —
    the ``ActorRef.kind`` field on ``AuditRecordV1`` (EXECUTION_POLICY.md
    §8). Always one of these three; never free text.
    """

    AGENT = "AGENT"
    SERVICE = "SERVICE"
    HUMAN = "HUMAN"


class PolicyDenyReason(str, Enum):
    """Fixed vocabulary of policy-check deny codes
    (``docs/security/EXECUTION_POLICY.md`` §3.2). A ``PolicyDecisionV1``
    denial's ``reason`` is always one of these, never free text, so
    detection/alerting tooling ("the agent is trying to escalate") can
    pattern-match reliably instead of parsing prose.
    """

    BAD_TOKEN_SIGNATURE = "BAD_TOKEN_SIGNATURE"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_SCOPE_MISMATCH = "TOKEN_SCOPE_MISMATCH"
    UNKNOWN_RANGE = "UNKNOWN_RANGE"
    TARGET_NOT_IN_RANGE = "TARGET_NOT_IN_RANGE"
    CAPABILITY_NOT_GRANTED = "CAPABILITY_NOT_GRANTED"
    ABILITY_NOT_IN_CATALOG = "ABILITY_NOT_IN_CATALOG"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    HUMAN_APPROVAL_REQUIRED = "HUMAN_APPROVAL_REQUIRED"
    OFF_RANGE_TARGET_ABSOLUTE_DENY = "OFF_RANGE_TARGET_ABSOLUTE_DENY"
    POLICY_SERVICE_UNAVAILABLE = "POLICY_SERVICE_UNAVAILABLE"
