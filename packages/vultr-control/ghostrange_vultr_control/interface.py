"""The stable provider interface every Vultr-control implementation honors.

``packages/range-runtime`` and ``packages/range-iac`` are built against this
ABC, not against ``RealVultrProvider``/``MockVultrProvider`` directly, so
either implementation can be swapped in behind it. If this interface's shape
must change, that is a breaking change for those two packages — see this
package's README, "Interface stability" section, before changing method
signatures here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .models import ComputeRecord, CreateComputeRequest, CreateWorldRequest, WorldRecord


class VultrControlProvider(ABC):
    """Create/inspect/reconcile/destroy Vultr worlds (VPC + firewall group)
    and compute (instances) attached to them.

    A "world" here is the Vultr-level network isolation unit backing one
    GhostRange ``WorldV1`` — one VPC 2.0-equivalent network per ADR-006,
    optionally paired with a dedicated Firewall Group. A "compute" is one
    Vultr Compute instance (a range asset), always attached to exactly one
    world.

    Every method must raise a subclass of
    ``ghostrange_vultr_control.errors.VultrControlError`` on failure — never
    a raw transport exception.
    """

    # ---- world (VPC + firewall group) ---------------------------------

    @abstractmethod
    def create_world(self, req: CreateWorldRequest) -> WorldRecord:
        """Create a new isolation unit for a World. Idempotency is the
        caller's responsibility (Vultr's create-VPC call is not itself
        idempotent) — callers should not retry a timed-out create_world call
        blindly without checking whether it actually landed."""

    @abstractmethod
    def get_world(self, provider_world_id: str) -> WorldRecord:
        """Fetch current state. Raises ``VultrNotFoundError`` if gone."""

    @abstractmethod
    def destroy_world(
        self,
        provider_world_id: str,
        *,
        firewall_group_id: Optional[str] = None,
        timeout_s: float = 120.0,
        poll_interval_s: float = 3.0,
    ) -> None:
        """Delete the world's VPC (and, if given, its paired firewall group),
        and confirm each is actually gone (not just that DELETE returned
        2xx) before returning. Raises ``VultrTimeoutError`` if deletion is
        not confirmed within ``timeout_s``. Callers should destroy every
        compute attached to this world *before* calling this — a provider
        implementation is not required to cascade-delete attached instances.
        """

    @abstractmethod
    def list_worlds(self, *, range_id: Optional[str] = None) -> list[WorldRecord]:
        """List known worlds, optionally filtered to one Range's ownership
        tag. Used by orphan-detection sweeps. Resources with no parseable
        GhostRange ownership metadata are excluded whenever ``range_id`` is
        given (there is nothing to match against); pass ``range_id=None`` to
        see every world this credential's account can see, tagged or not.
        """

    # ---- compute (instances) -------------------------------------------

    @abstractmethod
    def create_compute(self, req: CreateComputeRequest) -> ComputeRecord:
        """Create one instance attached to ``req.world_ref``. Does not wait
        for it to become ready — call ``wait_until_ready`` for that."""

    @abstractmethod
    def get_compute(self, provider_compute_id: str) -> ComputeRecord:
        """Fetch current state. Raises ``VultrNotFoundError`` if gone."""

    @abstractmethod
    def wait_until_ready(
        self,
        provider_compute_id: str,
        *,
        timeout_s: float = 300.0,
        poll_interval_s: float = 5.0,
    ) -> ComputeRecord:
        """Poll until the instance reaches ``ResourceStatus.ACTIVE`` or
        ``timeout_s`` elapses. Raises ``VultrTimeoutError`` on timeout,
        ``VultrNotFoundError`` if the instance disappears while waiting.

        Readiness here means "Vultr's own API reports the instance active"
        — it does NOT mean cloud-init has finished configuring the OS
        (Vultr's own docs put that at ~10 more minutes; see this package's
        README). Callers that need that finer signal must probe it
        themselves (e.g. via the instance's metadata service or an
        application-level health check), not through this method.
        """

    @abstractmethod
    def destroy_compute(
        self,
        provider_compute_id: str,
        *,
        timeout_s: float = 120.0,
        poll_interval_s: float = 3.0,
    ) -> None:
        """Delete the instance and confirm it is actually gone (not just
        that DELETE returned 2xx) before returning. Raises
        ``VultrTimeoutError`` if deletion is not confirmed within
        ``timeout_s``."""

    @abstractmethod
    def list_computes(self, *, range_id: Optional[str] = None) -> list[ComputeRecord]:
        """List known compute instances, optionally filtered to one Range's
        ownership tag. Used by orphan-detection sweeps (see ``list_worlds``
        for the same caveat about untagged resources)."""


__all__ = ["VultrControlProvider"]
