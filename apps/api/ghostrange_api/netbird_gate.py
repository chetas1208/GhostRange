"""NetBird mesh-enrollment readiness gate for GhostRange workers.

Feature-flagged end to end by ``Settings.netbird_enabled`` (``NETBIRD_ENABLED``,
currently ``false``). When disabled, every function here is a documented
no-op — the worker readiness gate behaves *exactly* as it did before NetBird
was added: Vultr VM running + GhostRange worker registered + heartbeat is
still the entire gate. When enabled, a worker is not considered fully READY
until it *additionally* has a NetBird peer that is (a) connected to the
NetBird management server and (b) a member of ``NETBIRD_WORKER_GROUP``
(default ``ghostrange-workers``) — connectivity alone is not enough, because
micro-segmentation policy only applies to peers actually in the right group.

Integration point
----------------------------------------------------------------------
The live provisioning flow calls this module from
``RealWorkerOrchestrator.run_cpu_benchmark_test``:

1. Construct a client once (e.g. in ``main.py``'s lifespan — already done,
   see ``app.state.netbird_client``) and pass it into
   ``RealWorkerOrchestrator.__init__``.
2. After the existing line::

       await self._store.wait_worker_registered(worker_id, timeout_s=120.0)

   and before::

       task = await self._store.wait_task_completed(run_id, timeout_s=180.0)

   insert::

       await ensure_worker_mesh_ready(
           settings=self._settings,
           store=self._store,
           client=self._netbird_client,
           worker_id=worker_id,
           peer_hostname=f"gr-worker-{str(worker_id)[:8]}",  # matches
               # VultrComputeProvider.create_worker's `hostname=f"gr-worker-{suffix}"`
       )

   ``ensure_worker_mesh_ready`` raises ``NetBirdBootstrapFailed`` on timeout
   (having already recorded ``BOOTSTRAP_FAILED`` via
   ``store.mark_worker_bootstrap_failed``) and returns immediately, doing
   nothing at all, when ``NETBIRD_ENABLED=false``. The existing
   ``try/finally`` in that method already calls
   ``provider.terminate_worker(handle)`` on *any* exception raised inside the
   ``try`` block — no new termination path is needed; raising
   ``NetBirdBootstrapFailed`` here reuses that exact mechanism.
3. Pass the setup key into cloud-init generation:
   ``worker_cloud_init(control_url=public_url, bootstrap_token=bootstrap,
   netbird_setup_key=self._settings.netbird_worker_setup_key if
   self._settings.netbird_enabled else None, netbird_peer_hostname=f"gr-worker-{...}")``.
4. On teardown (the ``finally`` block, right alongside
   ``provider.terminate_worker(handle)``), call
   ``revoke_worker_peer(self._settings, self._netbird_client, peer_hostname)``
   so a destroyed worker's mesh identity doesn't linger between the VM being
   gone and NetBird's own stale-peer cleanup.

The integration is live-only. Mock workers continue to use the existing
in-process agent and are not expected to enroll in an external mesh.
"""

from __future__ import annotations

import asyncio
import time
import uuid

from ghostrange_netbird_control import NetBirdClient, NetBirdControlError

from .config import Settings
from .worker_store import WorkerStore


class NetBirdBootstrapFailed(RuntimeError):
    """Raised when a worker's NetBird peer never became connected + a
    member of the required group within the enrollment timeout. By the time
    this is raised, the worker has already been marked BOOTSTRAP_FAILED in
    the store (with a reason) — the caller only needs to terminate the
    underlying compute resource."""


def build_netbird_client(settings: Settings) -> NetBirdClient | None:
    """Returns ``None`` when NetBird is disabled — the normal, current
    state (``NETBIRD_ENABLED=false``). Raises loudly (does not silently
    disable) if ``NETBIRD_ENABLED=true`` but a required credential is
    missing, since a half-configured flag flip is a misconfiguration, not a
    valid "off" state."""
    if not settings.netbird_enabled:
        return None
    if not settings.netbird_api_token:
        raise RuntimeError("NETBIRD_ENABLED=true requires NETBIRD_API_TOKEN to be set")
    if not settings.netbird_worker_setup_key:
        raise RuntimeError("NETBIRD_ENABLED=true requires NETBIRD_WORKER_SETUP_KEY to be set")
    return NetBirdClient(api_token=settings.netbird_api_token, base_url=settings.netbird_api_base_url)


async def ensure_worker_mesh_ready(
    *,
    settings: Settings,
    store: WorkerStore,
    client: NetBirdClient | None,
    worker_id: uuid.UUID,
    peer_hostname: str,
    timeout_s: float | None = None,
    poll_s: float = 3.0,
) -> None:
    """Block (async) until ``peer_hostname`` is a NetBird peer that is
    connected AND a member of ``settings.netbird_worker_group``, or raise
    ``NetBirdBootstrapFailed`` after the timeout.

    A complete no-op — returns immediately, makes no NetBird API call at
    all — when ``settings.netbird_enabled`` is False. This is the exact
    inertness contract required before this feature may be turned on for
    real: with the flag off, calling this function has zero observable
    effect on the readiness gate.
    """
    if not settings.netbird_enabled:
        return
    if client is None:
        raise RuntimeError("ensure_worker_mesh_ready called with NETBIRD_ENABLED=true but no NetBirdClient")

    group = settings.netbird_worker_group
    budget = timeout_s if timeout_s is not None else settings.netbird_enroll_timeout_s
    deadline = time.monotonic() + budget

    while True:
        peer = await asyncio.to_thread(client.find_peer_by_name, peer_hostname)
        if peer is not None and client.is_peer_ready(peer, group=group):
            return
        if time.monotonic() >= deadline:
            reason = (
                f"NetBird peer '{peer_hostname}' did not become connected + a member of "
                f"group '{group}' within {budget:.0f}s"
                + ("" if peer is None else f" (last seen: connected={peer.connected}, groups={sorted(peer.group_names)})")
            )
            await store.mark_worker_bootstrap_failed(worker_id, reason=reason)
            raise NetBirdBootstrapFailed(reason)
        await asyncio.sleep(poll_s)


def revoke_worker_peer(settings: Settings, client: NetBirdClient | None, peer_hostname: str) -> None:
    """Teardown hook: revoke a worker's NetBird peer, e.g. right alongside
    ``provider.terminate_worker(handle)``. No-op when NetBird is disabled or
    no matching peer exists (nothing to revoke) — never raises for "already
    gone" states, since worker teardown must not be blocked by mesh cleanup
    failing to find something that's already cleaned up.

    Swallows (logs via the raised exception's message not being reraised)
    NetBirdControlError so a NetBird-side outage never prevents the
    Vultr VM teardown this is called alongside from completing — the
    stale peer becomes an operational cleanup item rather than a stuck
    worker teardown.
    """
    if not settings.netbird_enabled or client is None:
        return
    try:
        client.revoke_peer_by_name(peer_hostname)
    except NetBirdControlError:
        # Best-effort: a stale NetBird peer left behind by an API outage is
        # a much smaller problem than a worker teardown that never
        # completes. Surface this in real deployments via logging once
        # this is wired into worker_orchestrator.py.
        pass


__all__ = [
    "NetBirdBootstrapFailed",
    "build_netbird_client",
    "ensure_worker_mesh_ready",
    "revoke_worker_peer",
]
