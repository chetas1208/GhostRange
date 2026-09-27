from __future__ import annotations

import os
import uuid
from datetime import timedelta

import pytest
from ghostrange_contracts.enums import AbilityCategory, PolicyActorKind
from ghostrange_contracts.policy import ActorRef, ExecutionRequestV1, ProvenanceRef, TargetRef

from ghostrange_policy_check import AuditLog, PolicyCheckService, PolicyRegistry, TokenSigner

TEST_SIGNING_KEY = b"test-signing-key-not-for-prod-use"


@pytest.fixture()
def signer() -> TokenSigner:
    return TokenSigner(key=TEST_SIGNING_KEY)


@pytest.fixture()
def registry() -> PolicyRegistry:
    return PolicyRegistry()


@pytest.fixture()
def audit_log() -> AuditLog:
    return AuditLog()


@pytest.fixture()
def service(registry, signer, audit_log) -> PolicyCheckService:
    return PolicyCheckService(registry, signer, audit_log)


@pytest.fixture()
def world_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture()
def range_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture()
def in_range_targets(range_id) -> list[TargetRef]:
    return [
        TargetRef(range_id=range_id, host_or_ip="10.20.0.5"),
        TargetRef(range_id=range_id, host_or_ip="10.20.0.6"),
    ]


@pytest.fixture()
def off_range_target(range_id) -> TargetRef:
    """A ``TargetRef`` that carries the SAME range_id as the provisioned
    range (so it passes ``ExecutionRequestV1``'s own range-consistency
    contract validator) but names a host that was never actually
    provisioned into that range's registry entry. This is the realistic
    "the agent/attacker names a plausible-looking off-range host" case
    that only policy-check's registry re-derivation (not schema validation
    alone) can catch -- exactly the T5/T10 backstop.
    """
    return TargetRef(range_id=range_id, host_or_ip="203.0.113.99")


@pytest.fixture()
def provisioned_range(registry, range_id, world_id, in_range_targets):
    """Registers the range's canonical target set + a quota + one reviewed
    ability, standing in for what range-runtime's provisioning pipeline
    does at real range-creation time.
    """
    registry.register_range(range_id, in_range_targets)
    registry.set_quota(world_id, max_cost=100.0)
    registry.register_ability("attack.discovery.host")
    return range_id


@pytest.fixture()
def valid_token(signer, world_id, provisioned_range, in_range_targets):
    return signer.mint_token(
        world_id=world_id,
        range_id=provisioned_range,
        target_set=in_range_targets,
        capabilities=[AbilityCategory.RECON],
        ttl=timedelta(minutes=10),
    )


@pytest.fixture()
def actor() -> ActorRef:
    return ActorRef(kind=PolicyActorKind.AGENT, id="agent-1", tool_call_id="call-1")


@pytest.fixture()
def provenance() -> ProvenanceRef:
    return ProvenanceRef(package="ghostrange_policy_check.tests", version="0.1.0")


def make_request(*, world_id, range_id, target_refs, action_category=AbilityCategory.RECON,
                  ability_ref="attack.discovery.host", resource_cost=0.0, **overrides):
    defaults = dict(
        task_id=uuid.uuid4(),
        world_id=world_id,
        range_id=range_id,
        target_refs=target_refs,
        action_category=action_category,
        ability_ref=ability_ref,
        requested_by="agent-tool-call-1",
        resource_cost=resource_cost,
    )
    defaults.update(overrides)
    return ExecutionRequestV1(**defaults)
