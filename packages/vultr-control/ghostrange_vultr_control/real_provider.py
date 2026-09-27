"""RealVultrProvider: talks to the actual Vultr API v2 (https://api.vultr.com).

Endpoint/field shapes used here are documented in this package's README, and
were each verified on 2026-09-26 against the current `govultr` v3 Go SDK
source (https://github.com/vultr/govultr), which mirrors the live API v2
request/response schema 1:1 — this is more reliable than the interactive API
reference page (which is a JS SPA that can't be fetched headlessly) or
marketing docs, though it is still NOT the same as a live call against the
real API. See README.md "REAL_VULTR_E2E" for exactly what has and has not
been verified end-to-end.

This module never fabricates a successful call. If ``VULTR_API_KEY`` is
unset, constructing this class raises ``VultrAuthError`` immediately (see
``VultrHTTPClient.__init__``) rather than silently degrading to mock
behavior.
"""

from __future__ import annotations

import base64
import time
from datetime import datetime
from typing import Any, Optional

from .errors import VultrControlError, VultrNotFoundError, VultrTimeoutError
from .http_client import DEFAULT_BASE_URL, VultrHTTPClient
from .interface import VultrControlProvider
from .models import (
    ComputeRecord,
    CreateComputeRequest,
    CreateWorldRequest,
    utc_now,
    GhostRangeTags,
    ProviderKind,
    ResourceStatus,
    WorldRecord,
)


def _map_instance_status(status: Optional[str]) -> ResourceStatus:
    """Vultr instance ``status`` values observed/documented: "pending",
    "active", "suspended", "resizing". We map the two we can act on
    confidently and treat everything else as PENDING (not-yet-usable) rather
    than guessing — a caller polling wait_until_ready will simply keep
    waiting rather than being told something false."""
    if status == "active":
        return ResourceStatus.ACTIVE
    return ResourceStatus.PENDING


def _parse_vultr_datetime(raw: Optional[str]) -> datetime:
    """Parse Vultr's ``date_created`` (ISO 8601, e.g. "2020-10-10T01:56:20+00:00").

    Falls back to ``utc_now()`` only when the field is missing/unparseable —
    never crashes a list call over a formatting surprise, but this must
    never be relied on as "the real creation time" when it happens: an
    orphan-reaper comparing this to a TTL needs the REAL timestamp, and a
    silent fallback to "now" would make every instance look freshly created
    forever. Callers should treat an unparseable date_created as worth
    investigating, not routine.
    """
    if not raw:
        return utc_now()
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return utc_now()


class RealVultrProvider(VultrControlProvider):
    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        http_client: Optional[VultrHTTPClient] = None,
        requests_per_second: float = 15.0,
        max_retries: int = 5,
    ) -> None:
        self._http = http_client or VultrHTTPClient(
            api_key=api_key,
            base_url=base_url,
            requests_per_second=requests_per_second,
            max_retries=max_retries,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "RealVultrProvider":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # ---- world (VPC + firewall group) ----------------------------------

    def create_world(self, req: CreateWorldRequest) -> WorldRecord:
        vpc_body: dict[str, Any] = {
            "region": req.region,
            "description": req.tags.as_description(),
        }
        if req.v4_subnet:
            vpc_body["v4_subnet"] = req.v4_subnet
        if req.v4_subnet_mask is not None:
            vpc_body["v4_subnet_mask"] = req.v4_subnet_mask

        vpc_resp = self._http.request("POST", "/v2/vpcs", json_body=vpc_body)
        vpc = vpc_resp["vpc"]

        firewall_group_id: Optional[str] = None
        if req.create_firewall_group:
            fw_resp = self._http.request(
                "POST", "/v2/firewalls", json_body={"description": req.tags.as_description()}
            )
            firewall_group_id = fw_resp["firewall_group"]["id"]

        return WorldRecord(
            provider=ProviderKind.VULTR,
            provider_world_id=vpc["id"],
            firewall_group_id=firewall_group_id,
            region=vpc["region"],
            v4_subnet=vpc.get("v4_subnet"),
            v4_subnet_mask=vpc.get("v4_subnet_mask"),
            status=ResourceStatus.ACTIVE,
            tags=req.tags,
            raw={"vpc": vpc},
        )

    def get_world(self, provider_world_id: str) -> WorldRecord:
        resp = self._http.request("GET", f"/v2/vpcs/{provider_world_id}")
        vpc = resp["vpc"]
        return WorldRecord(
            provider=ProviderKind.VULTR,
            provider_world_id=vpc["id"],
            region=vpc["region"],
            v4_subnet=vpc.get("v4_subnet"),
            v4_subnet_mask=vpc.get("v4_subnet_mask"),
            status=ResourceStatus.ACTIVE,
            tags=GhostRangeTags.from_description(vpc.get("description")),
            raw={"vpc": vpc},
        )

    def destroy_world(
        self,
        provider_world_id: str,
        *,
        firewall_group_id: Optional[str] = None,
        timeout_s: float = 120.0,
        poll_interval_s: float = 3.0,
    ) -> None:
        self._http.request("DELETE", f"/v2/vpcs/{provider_world_id}")
        self._poll_until_gone(
            lambda: self._http.request("GET", f"/v2/vpcs/{provider_world_id}"),
            timeout_s=timeout_s,
            poll_interval_s=poll_interval_s,
            what=f"vpc {provider_world_id}",
        )
        if firewall_group_id:
            self._http.request("DELETE", f"/v2/firewalls/{firewall_group_id}")
            self._poll_until_gone(
                lambda: self._http.request("GET", f"/v2/firewalls/{firewall_group_id}"),
                timeout_s=timeout_s,
                poll_interval_s=poll_interval_s,
                what=f"firewall group {firewall_group_id}",
            )

    def list_worlds(self, *, range_id: Optional[str] = None) -> list[WorldRecord]:
        """GhostRange-owned VPCs only — untagged VPCs never returned (mirrors ``list_computes``)."""
        resp = self._http.request("GET", "/v2/vpcs")
        records: list[WorldRecord] = []
        for vpc in resp.get("vpcs", []):
            tags = GhostRangeTags.from_description(vpc.get("description"))
            if tags is None:
                continue
            if range_id is not None and tags.range_id != range_id:
                continue
            records.append(
                WorldRecord(
                    provider=ProviderKind.VULTR,
                    provider_world_id=vpc["id"],
                    region=vpc["region"],
                    v4_subnet=vpc.get("v4_subnet"),
                    v4_subnet_mask=vpc.get("v4_subnet_mask"),
                    status=ResourceStatus.ACTIVE,
                    tags=tags,
                    raw={"vpc": vpc},
                )
            )
        return records

    # ---- compute (instances) --------------------------------------------

    def create_compute(self, req: CreateComputeRequest) -> ComputeRecord:
        body: dict[str, Any] = {
            "region": req.region,
            "plan": req.plan,
            "tags": req.tags.as_vultr_tag_list(),
            "attach_vpc": [req.world_ref],
            "backups": "enabled" if req.backups else "disabled",
        }
        if req.os_id is not None:
            body["os_id"] = req.os_id
        if req.snapshot_id is not None:
            body["snapshot_id"] = req.snapshot_id
        if req.script_id:
            body["script_id"] = req.script_id
        if req.user_data:
            body["user_data"] = base64.b64encode(req.user_data.encode("utf-8")).decode("ascii")
        if req.firewall_group_id:
            body["firewall_group_id"] = req.firewall_group_id
        if req.hostname:
            body["hostname"] = req.hostname
        if req.label:
            body["label"] = req.label
        if req.enable_ipv6:
            body["enable_ipv6"] = True

        resp = self._http.request("POST", "/v2/instances", json_body=body)
        return self._compute_record_from_api(resp["instance"], tags=req.tags, world_ref=req.world_ref)

    def get_compute(self, provider_compute_id: str) -> ComputeRecord:
        resp = self._http.request("GET", f"/v2/instances/{provider_compute_id}")
        instance = resp["instance"]
        tags = GhostRangeTags.from_vultr_tag_list(instance.get("tags") or [])
        world_ref = self._lookup_world_ref(provider_compute_id)
        return self._compute_record_from_api(instance, tags=tags, world_ref=world_ref)

    def _lookup_world_ref(self, provider_compute_id: str) -> Optional[str]:
        """Best-effort: the instance GET response does not itself include
        attached VPC ids, so this issues a second call to
        `/v2/instances/{id}/vpcs`. Failure here is non-fatal — world_ref is
        informational on a fetched record, never load-bearing for callers
        that already tracked it from create_compute."""
        try:
            resp = self._http.request("GET", f"/v2/instances/{provider_compute_id}/vpcs")
        except VultrControlError:
            return None
        vpcs = resp.get("vpcs") or [] if isinstance(resp, dict) else []
        return vpcs[0]["id"] if vpcs else None

    def wait_until_ready(
        self,
        provider_compute_id: str,
        *,
        timeout_s: float = 300.0,
        poll_interval_s: float = 5.0,
    ) -> ComputeRecord:
        deadline = time.monotonic() + timeout_s
        while True:
            record = self.get_compute(provider_compute_id)
            if record.status == ResourceStatus.ACTIVE:
                return record
            if time.monotonic() >= deadline:
                raise VultrTimeoutError(
                    f"instance {provider_compute_id} not active after {timeout_s}s "
                    f"(last status={record.status.value}, power_status={record.vultr_power_status!r}, "
                    f"server_status={record.vultr_server_status!r})"
                )
            time.sleep(poll_interval_s)

    def destroy_compute(
        self,
        provider_compute_id: str,
        *,
        timeout_s: float = 120.0,
        poll_interval_s: float = 3.0,
    ) -> None:
        self._http.request("DELETE", f"/v2/instances/{provider_compute_id}")
        self._poll_until_gone(
            lambda: self._http.request("GET", f"/v2/instances/{provider_compute_id}"),
            timeout_s=timeout_s,
            poll_interval_s=poll_interval_s,
            what=f"instance {provider_compute_id}",
        )

    def list_computes(self, *, range_id: Optional[str] = None) -> list[ComputeRecord]:
        """List GhostRange-owned instances only.

        Ownership is required regardless of ``range_id``: an instance with
        no parseable GhostRange tags (``GhostRangeTags.from_vultr_tag_list``
        returns ``None`` — not created by GhostRange, or missing the
        required ``range_id`` tag) is *never* returned, whether the caller
        asked for a specific range or for every GhostRange-owned instance
        (``range_id=None``, e.g. ``list_owned_workers(range_id=None)`` /
        ``list_all_ghostrange_workers()`` at teardown time). This is the
        set ``ShieldedComputeProvider`` treats as "ours" for the
        P1_UNOWNED_RESOURCE ownership check — an unfiltered account-wide
        list here would silently defeat that check.
        """
        resp = self._http.request("GET", "/v2/instances")
        records: list[ComputeRecord] = []
        for instance in resp.get("instances", []):
            tags = GhostRangeTags.from_vultr_tag_list(instance.get("tags") or [])
            if tags is None:
                continue
            if range_id is not None and tags.range_id != range_id:
                continue
            records.append(self._compute_record_from_api(instance, tags=tags, world_ref=None))
        return records

    # ---- shared helpers --------------------------------------------------

    @staticmethod
    def _compute_record_from_api(
        instance: dict[str, Any], *, tags: Optional[GhostRangeTags], world_ref: Optional[str]
    ) -> ComputeRecord:
        return ComputeRecord(
            provider=ProviderKind.VULTR,
            provider_compute_id=instance["id"],
            world_ref=world_ref,
            region=instance.get("region", ""),
            plan=instance.get("plan", ""),
            label=instance.get("label") or None,
            hostname=instance.get("hostname") or None,
            main_ip=instance.get("main_ip") or None,
            status=_map_instance_status(instance.get("status")),
            vultr_power_status=instance.get("power_status"),
            vultr_server_status=instance.get("server_status"),
            tags=tags,
            created_at=_parse_vultr_datetime(instance.get("date_created")),
            raw={"instance": instance},
        )

    @staticmethod
    def _poll_until_gone(fetch: Any, *, timeout_s: float, poll_interval_s: float, what: str) -> None:
        """Confirm deletion: a 2xx on DELETE does not mean the resource is
        actually gone. Poll GET until it 404s (success) or timeout_s
        elapses (raise)."""
        deadline = time.monotonic() + timeout_s
        while True:
            try:
                fetch()
            except VultrNotFoundError:
                return
            if time.monotonic() >= deadline:
                raise VultrTimeoutError(f"{what} still present after {timeout_s}s; deletion not confirmed")
            time.sleep(poll_interval_s)


__all__ = ["RealVultrProvider"]
