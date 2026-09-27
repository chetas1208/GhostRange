"""ProvenanceStore: register evidence-chain records, traverse them, and
enforce that a Claim can only be marked verified if real evidence backs
it.

This is the concrete implementation behind two requirements:

1. **Provenance queries** -- given a ``ClaimV1``, retrieve its full
   evidence chain (Claim -> Evidence -> Verification -> Observation ->
   ExecutionRecord -> World -> Artifact) as one traversable structure.
   This is what the Evidence 3D view (a separate frontend session) is
   expected to eventually query -- see :func:`ProvenanceStore.get_provenance_chain`
   and :class:`ProvenanceChain` for the exact shape, documented as the
   query API/response contract for that consumer.
2. **Claim verification gating** -- ``ClaimV1`` (packages/contracts) has
   no ``verified``/``status`` field of its own (deliberately: whether/how
   a Claim's stated confidence should move on verification result is
   flagged in EVIDENCE.md as "a policy decision, not a schema one," left
   to this package). This module owns that policy:
   :func:`ProvenanceStore.mark_claim_verified` raises
   :class:`~ghostrange_evidence.exceptions.NoEvidenceError` if a Claim has
   zero ``EvidenceV1`` bundles -- structurally, a claim with no evidence
   cannot become VERIFIED through this API, there is no code path that
   sets that status without a real Evidence bundle backing it.

## Storage note

This is an in-memory reference implementation: dicts keyed by id, plus a
few reverse-lookup indices built at registration time. That's the right
scope for M2 (single-process backend, no live traffic yet) and it isolates
the *query shape* other consumers should code against from the eventual
backing store. Per docs/research/VULTR.md's own plan ("Postgres holds
metadata/pointers, not the blobs themselves"), swapping this for a real
Postgres-backed repository later should only require re-implementing this
class's public methods against SQL, not changing any caller -- none of
the query methods below leak the fact that they're currently dict lookups.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from ghostrange_contracts.enums import VerificationResult
from ghostrange_contracts.evidence import ArtifactV1, ClaimV1, EvidenceV1
from ghostrange_contracts.execution_graph import ExecutionRecordV1
from ghostrange_contracts.verification import ObservationV1, VerificationV1
from ghostrange_contracts.world import WorldV1

from .exceptions import NoEvidenceError, UnknownReferenceError


class ClaimVerificationStatus:
    """String constants for the derived (non-contract) status this package
    tracks per Claim. Deliberately plain string constants, not a pydantic
    enum on a contract model -- this status lives entirely in
    ``packages/evidence``'s policy layer, not in the frozen contracts
    schema (see module docstring)."""

    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    REFUTED = "REFUTED"


@dataclass(frozen=True)
class ObservationChainLink:
    """One Observation plus everything it resolves to going *down* the
    chain: the ExecutionRecord it came from, that execution's World, and
    every Artifact reachable from either the Observation itself
    (``raw_artifact_id``) or its ExecutionRecord (``artifact_ids``)."""

    observation: ObservationV1
    execution_record: ExecutionRecordV1 | None
    world: WorldV1 | None
    artifacts: tuple[ArtifactV1, ...]


@dataclass(frozen=True)
class EvidenceChainLink:
    """One EvidenceV1 bundle plus its resolved Verification and every
    Observation (with their own downstream chain) it cites."""

    evidence: EvidenceV1
    verification: VerificationV1 | None
    observations: tuple[ObservationChainLink, ...]
    # Artifacts referenced directly on the EvidenceV1 bundle itself
    # (EvidenceV1.artifact_ids), distinct from artifacts reachable via an
    # individual Observation -- kept separate because EVIDENCE.md
    # deliberately allows an Evidence bundle to carry artifact references
    # that summarize/aggregate beyond any single Observation's own pointer.
    bundle_artifacts: tuple[ArtifactV1, ...]


@dataclass(frozen=True)
class ProvenanceChain:
    """The full traversable structure for one Claim: this is the query
    response shape the Evidence 3D view (or any other consumer) should
    code against.

        ProvenanceChain
          .claim               -> ClaimV1
          .verification_status -> one of ClaimVerificationStatus.*
          .evidence             -> tuple[EvidenceChainLink, ...]
              .evidence         -> EvidenceV1
              .verification     -> VerificationV1 | None
              .bundle_artifacts -> tuple[ArtifactV1, ...]
              .observations     -> tuple[ObservationChainLink, ...]
                  .observation       -> ObservationV1
                  .execution_record  -> ExecutionRecordV1 | None
                  .world             -> WorldV1 | None
                  .artifacts         -> tuple[ArtifactV1, ...]

    Every level may be empty (a Claim with no Evidence yet has
    ``evidence == ()``) but never raises on a merely-absent-so-far chain --
    it only raises (``UnknownReferenceError``, from the registration APIs
    below) when an id *is* referenced but does not resolve to any
    registered record, which is a data-integrity problem rather than an
    "evidence doesn't exist yet" state.
    """

    claim: ClaimV1
    verification_status: str
    evidence: tuple[EvidenceChainLink, ...]


class ProvenanceStore:
    """In-memory registry + query engine for the evidence chain.

    Records are registered as they're produced by the rest of the system
    (range-runtime, execution-graph, adversary-adapter, verifier agents,
    ...); this class never constructs domain objects itself (that's
    ``ArtifactStore`` for Artifacts, and each producing package for
    everything else) -- it only indexes what it's given and answers
    queries over it.
    """

    def __init__(self) -> None:
        self._claims: dict[uuid.UUID, ClaimV1] = {}
        self._evidence: dict[uuid.UUID, EvidenceV1] = {}
        self._verifications: dict[uuid.UUID, VerificationV1] = {}
        self._observations: dict[uuid.UUID, ObservationV1] = {}
        self._execution_records: dict[uuid.UUID, ExecutionRecordV1] = {}
        self._worlds: dict[uuid.UUID, WorldV1] = {}
        self._artifacts: dict[uuid.UUID, ArtifactV1] = {}

        # Reverse indices.
        self._evidence_by_claim: dict[uuid.UUID, list[uuid.UUID]] = {}

        # Derived, policy-layer status -- see ClaimVerificationStatus.
        self._claim_status: dict[uuid.UUID, str] = {}

    # -- Registration ----------------------------------------------------
    # Each `register_*` is idempotent-by-id (re-registering the same id
    # with identical content is a no-op-ish overwrite; these are ordinary
    # mutable dict entries, unlike the content-addressed, immutable
    # Artifact bytes in `object_store.py` -- metadata records here are
    # expected to be updated in place, e.g. a VerificationV1's `result`
    # transitioning from PENDING to PASSED/FAILED is a normal update, not
    # a tamper event).

    def register_world(self, world: WorldV1) -> None:
        self._worlds[world.id] = world

    def register_execution_record(self, record: ExecutionRecordV1) -> None:
        self._execution_records[record.id] = record

    def register_artifact(self, artifact: ArtifactV1) -> None:
        self._artifacts[artifact.id] = artifact

    def register_observation(self, observation: ObservationV1) -> None:
        self._observations[observation.id] = observation

    def register_verification(self, verification: VerificationV1) -> None:
        self._verifications[verification.id] = verification

    def register_claim(self, claim: ClaimV1) -> None:
        self._claims[claim.id] = claim
        self._claim_status.setdefault(claim.id, ClaimVerificationStatus.UNVERIFIED)

    def register_evidence(self, evidence: EvidenceV1) -> None:
        self._evidence[evidence.id] = evidence
        self._evidence_by_claim.setdefault(evidence.claim_id, [])
        if evidence.id not in self._evidence_by_claim[evidence.claim_id]:
            self._evidence_by_claim[evidence.claim_id].append(evidence.id)

    # -- Point lookups -----------------------------------------------------

    def get_claim(self, claim_id: uuid.UUID) -> ClaimV1:
        try:
            return self._claims[claim_id]
        except KeyError as exc:
            raise UnknownReferenceError(f"no ClaimV1 registered for id {claim_id}") from exc

    def get_claim_status(self, claim_id: uuid.UUID) -> str:
        """Current derived verification status for a Claim.

        Returns ``ClaimVerificationStatus.UNVERIFIED`` for a known Claim
        that has never been successfully marked verified/refuted, and
        raises ``UnknownReferenceError`` if ``claim_id`` was never
        registered at all (distinguishing "not verified yet" from
        "doesn't exist").
        """
        if claim_id not in self._claims:
            raise UnknownReferenceError(f"no ClaimV1 registered for id {claim_id}")
        return self._claim_status.get(claim_id, ClaimVerificationStatus.UNVERIFIED)

    # -- Claim verification gating ----------------------------------------

    def mark_claim_verified(self, claim_id: uuid.UUID) -> str:
        """Attempt to mark ``claim_id`` as verified, deriving the status
        from its linked Evidence/Verification records.

        Enforcement, in order:

        1. The Claim must be registered at all (``UnknownReferenceError``
           otherwise).
        2. The Claim must have at least one registered ``EvidenceV1``
           bundle (``NoEvidenceError`` otherwise) -- **this is the
           structural "zero evidence -> cannot be verified" gate.** It is
           checked here even though ``EvidenceV1.observation_ids`` already
           has ``min_length=1`` enforced by ``packages/contracts`` at
           construction time, because that earlier guarantee only holds
           for evidence that was actually constructed through the
           Pydantic model -- this layer is the one that additionally
           guarantees a Claim with *no evidence bundles registered at
           all* (the more basic failure mode: nobody ever verified this
           claim) cannot reach VERIFIED, regardless of how any individual
           EvidenceV1 was built.
        3. Defense-in-depth re-check: every registered EvidenceV1 for this
           claim must itself have at least one observation id (redundant
           with the contract-level guarantee for any EvidenceV1 that went
           through real construction, but this store's registration API
           accepts already-built model instances, which could in
           principle have been constructed via
           ``EvidenceV1.model_construct`` bypassing validation -- so this
           layer does not blindly trust that every registered object
           necessarily passed validation).
        4. The status is then derived from the linked Verification
           results: VERIFIED if any linked Verification PASSED, REFUTED if
           none PASSED but at least one FAILED, otherwise left UNVERIFIED
           (e.g. all PENDING/INCONCLUSIVE).

        Returns the resulting ``ClaimVerificationStatus`` value.
        """
        if claim_id not in self._claims:
            raise UnknownReferenceError(f"no ClaimV1 registered for id {claim_id}")

        evidence_ids = self._evidence_by_claim.get(claim_id, [])
        if not evidence_ids:
            raise NoEvidenceError(
                f"claim {claim_id} has zero registered EvidenceV1 bundles; "
                "a claim cannot be marked verified without real evidence"
            )

        evidences = [self._evidence[eid] for eid in evidence_ids]
        for ev in evidences:
            if not ev.observation_ids:
                # See point 3 in the docstring above.
                raise NoEvidenceError(
                    f"claim {claim_id}: evidence bundle {ev.id} has zero "
                    "observation_ids; cannot count as verifying evidence"
                )

        linked_verifications = [
            self._verifications[ev.verification_id]
            for ev in evidences
            if ev.verification_id in self._verifications
        ]

        if any(v.result == VerificationResult.PASSED for v in linked_verifications):
            status = ClaimVerificationStatus.VERIFIED
        elif any(v.result == VerificationResult.FAILED for v in linked_verifications):
            status = ClaimVerificationStatus.REFUTED
        else:
            status = ClaimVerificationStatus.UNVERIFIED

        self._claim_status[claim_id] = status
        return status

    # -- Provenance chain traversal ----------------------------------------

    def get_provenance_chain(self, claim_id: uuid.UUID) -> ProvenanceChain:
        """Resolve the full CLAIM -> EVIDENCE -> VERIFICATION ->
        OBSERVATION -> EXECUTION -> WORLD -> ARTIFACT structure for one
        Claim. See :class:`ProvenanceChain` for the exact response shape.

        Raises ``UnknownReferenceError`` if ``claim_id`` itself is
        unregistered, or if any record *reachable* from it references an
        id that was never registered (a dangling reference is a data
        integrity bug worth surfacing distinctly, not a "no evidence yet"
        state -- see ``exceptions.py``).
        """
        claim = self.get_claim(claim_id)  # raises UnknownReferenceError if absent
        status = self.get_claim_status(claim_id)

        evidence_links: list[EvidenceChainLink] = []
        for evidence_id in self._evidence_by_claim.get(claim_id, []):
            evidence = self._evidence[evidence_id]
            evidence_links.append(self._resolve_evidence(evidence))

        return ProvenanceChain(
            claim=claim,
            verification_status=status,
            evidence=tuple(evidence_links),
        )

    def _resolve_evidence(self, evidence: EvidenceV1) -> EvidenceChainLink:
        if evidence.verification_id not in self._verifications:
            raise UnknownReferenceError(
                f"evidence {evidence.id} references verification "
                f"{evidence.verification_id}, which is not registered"
            )
        verification: VerificationV1 | None = self._verifications[evidence.verification_id]

        observation_links = tuple(
            self._resolve_observation(obs_id) for obs_id in evidence.observation_ids
        )
        bundle_artifacts = tuple(self._resolve_artifact(a_id) for a_id in evidence.artifact_ids)

        return EvidenceChainLink(
            evidence=evidence,
            verification=verification,
            observations=observation_links,
            bundle_artifacts=bundle_artifacts,
        )

    def _resolve_observation(self, observation_id: uuid.UUID) -> ObservationChainLink:
        if observation_id not in self._observations:
            raise UnknownReferenceError(
                f"observation {observation_id} is referenced but not registered"
            )
        observation = self._observations[observation_id]

        if observation.execution_id not in self._execution_records:
            raise UnknownReferenceError(
                f"observation {observation_id} references execution "
                f"{observation.execution_id}, which is not registered"
            )
        execution_record: ExecutionRecordV1 | None = self._execution_records[observation.execution_id]

        world: WorldV1 | None = None
        artifacts: list[ArtifactV1] = []

        if execution_record.world_id in self._worlds:
            world = self._worlds[execution_record.world_id]
        else:
            raise UnknownReferenceError(
                f"execution {execution_record.id} references world "
                f"{execution_record.world_id}, which is not registered"
            )
        for artifact_id in execution_record.artifact_ids:
            artifacts.append(self._resolve_artifact(artifact_id))

        if observation.raw_artifact_id is not None:
            raw_artifact = self._resolve_artifact(observation.raw_artifact_id)
            if raw_artifact.id not in {a.id for a in artifacts}:
                artifacts.append(raw_artifact)

        return ObservationChainLink(
            observation=observation,
            execution_record=execution_record,
            world=world,
            artifacts=tuple(artifacts),
        )

    def _resolve_artifact(self, artifact_id: uuid.UUID) -> ArtifactV1:
        if artifact_id not in self._artifacts:
            raise UnknownReferenceError(f"artifact {artifact_id} is referenced but not registered")
        return self._artifacts[artifact_id]


__all__ = [
    "ProvenanceStore",
    "ProvenanceChain",
    "EvidenceChainLink",
    "ObservationChainLink",
    "ClaimVerificationStatus",
]
