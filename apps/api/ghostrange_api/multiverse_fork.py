"""M3-style multi-world fork (mock provider) — bounded remediation branches."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from ghostrange_contracts._base import utc_now


@dataclass
class ForkWorld:
    world_id: uuid.UUID
    branch_label: str
    parent_world_id: uuid.UUID


@dataclass
class MultiverseForkResult:
    parent_world_id: uuid.UUID
    branches: list[ForkWorld] = field(default_factory=list)


def fork_remediation_worlds(parent_world_id: uuid.UUID, *, count: int = 3) -> MultiverseForkResult:
    count = max(2, min(count, 5))
    labels = ["Fix A", "Fix B", "Fix C", "Fix D", "Fix E"][:count]
    branches = [
        ForkWorld(world_id=uuid.uuid4(), branch_label=labels[i], parent_world_id=parent_world_id)
        for i in range(count)
    ]
    return MultiverseForkResult(parent_world_id=parent_world_id, branches=branches)


async def emit_fork_events(gateway, range_id: uuid.UUID, result: MultiverseForkResult) -> None:
    await gateway.append_legacy(
        range_id,
        {
            "event_name": "world.fork.started",
            "schema_version": "1",
            "occurred_at": utc_now().isoformat(),
            "parent_world_id": str(result.parent_world_id),
            "branch_count": len(result.branches),
        },
        source="multiverse_fork",
        world_id=result.parent_world_id,
    )
    for b in result.branches:
        await gateway.append_legacy(
            range_id,
            {
                "event_name": "world.fork.created",
                "schema_version": "1",
                "occurred_at": utc_now().isoformat(),
                "world_id": str(b.world_id),
                "parent_world_id": str(b.parent_world_id),
                "branch_label": b.branch_label,
                "status": "PROVISIONING",
            },
            source="multiverse_fork",
            world_id=b.world_id,
        )


__all__ = ["fork_remediation_worlds", "emit_fork_events", "MultiverseForkResult"]
