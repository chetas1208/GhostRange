"""A small stateful fake of the real Vultr REST API, used as an
httpx.MockTransport handler.

This is NOT MockVultrProvider (that's this package's own supported offline
fake, one layer up). This is a test-only double of Vultr's actual HTTP
surface, so RealVultrProvider's request/response handling can be exercised
end-to-end — construct request, send it, parse response, map errors — with
zero network access and no real credentials. Endpoint paths/response
envelopes match the current `govultr` v3 SDK source, cross-checked in this
package's README.
"""

from __future__ import annotations

import itertools
import json

import httpx


class FakeVultrServer:
    def __init__(self) -> None:
        self.vpcs: dict[str, dict] = {}
        self.firewall_groups: dict[str, dict] = {}
        self.instances: dict[str, dict] = {}
        self._vpc_seq = itertools.count(1)
        self._fwg_seq = itertools.count(1)
        self._instance_seq = itertools.count(1)
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        method = request.method
        path = request.url.path
        body = json.loads(request.content) if request.content else {}

        if path == "/v2/vpcs" and method == "POST":
            return self._create_vpc(body)
        if path == "/v2/vpcs" and method == "GET":
            return httpx.Response(200, json={"vpcs": list(self.vpcs.values()), "meta": {}})
        if path.startswith("/v2/vpcs/") and method == "GET":
            return self._get_vpc(path.rsplit("/", 1)[-1])
        if path.startswith("/v2/vpcs/") and method == "DELETE":
            return self._delete_vpc(path.rsplit("/", 1)[-1])

        if path == "/v2/firewalls" and method == "POST":
            return self._create_firewall_group(body)
        if path.startswith("/v2/firewalls/") and method == "GET":
            return self._get_firewall_group(path.rsplit("/", 1)[-1])
        if path.startswith("/v2/firewalls/") and method == "DELETE":
            return self._delete_firewall_group(path.rsplit("/", 1)[-1])

        if path == "/v2/instances" and method == "POST":
            return self._create_instance(body)
        if path == "/v2/instances" and method == "GET":
            return httpx.Response(200, json={"instances": list(self.instances.values()), "meta": {}})
        if path.startswith("/v2/instances/") and path.endswith("/vpcs") and method == "GET":
            instance_id = path.split("/")[3]
            instance = self.instances.get(instance_id)
            vpcs = [{"id": instance["_vpc_id"]}] if instance and instance.get("_vpc_id") else []
            return httpx.Response(200, json={"vpcs": vpcs, "meta": {}})
        if path.startswith("/v2/instances/") and method == "GET":
            return self._get_instance(path.rsplit("/", 1)[-1])
        if path.startswith("/v2/instances/") and method == "DELETE":
            return self._delete_instance(path.rsplit("/", 1)[-1])

        return httpx.Response(404, json={"error": f"no fake route for {method} {path}"})

    # -- vpcs ---------------------------------------------------------------

    def _create_vpc(self, body: dict) -> httpx.Response:
        vpc_id = f"vpc-{next(self._vpc_seq)}"
        vpc = {
            "id": vpc_id,
            "region": body["region"],
            "description": body.get("description", ""),
            "v4_subnet": body.get("v4_subnet", "10.0.0.0"),
            "v4_subnet_mask": body.get("v4_subnet_mask", 24),
            "date_created": "2026-09-26T00:00:00+00:00",
        }
        self.vpcs[vpc_id] = vpc
        return httpx.Response(202, json={"vpc": vpc})

    def _get_vpc(self, vpc_id: str) -> httpx.Response:
        vpc = self.vpcs.get(vpc_id)
        if vpc is None:
            return httpx.Response(404, json={"error": "VPC not found"})
        return httpx.Response(200, json={"vpc": vpc})

    def _delete_vpc(self, vpc_id: str) -> httpx.Response:
        if vpc_id not in self.vpcs:
            return httpx.Response(404, json={"error": "VPC not found"})
        del self.vpcs[vpc_id]
        return httpx.Response(204)

    # -- firewall groups ------------------------------------------------

    def _create_firewall_group(self, body: dict) -> httpx.Response:
        fwg_id = f"fwg-{next(self._fwg_seq)}"
        group = {
            "id": fwg_id,
            "description": body.get("description", ""),
            "date_created": "2026-09-26T00:00:00+00:00",
            "date_modified": "2026-09-26T00:00:00+00:00",
            "instance_count": 0,
            "rule_count": 0,
            "max_rule_count": 50,
        }
        self.firewall_groups[fwg_id] = group
        return httpx.Response(202, json={"firewall_group": group})

    def _get_firewall_group(self, fwg_id: str) -> httpx.Response:
        group = self.firewall_groups.get(fwg_id)
        if group is None:
            return httpx.Response(404, json={"error": "Firewall Group not found"})
        return httpx.Response(200, json={"firewall_group": group})

    def _delete_firewall_group(self, fwg_id: str) -> httpx.Response:
        if fwg_id not in self.firewall_groups:
            return httpx.Response(404, json={"error": "Firewall Group not found"})
        del self.firewall_groups[fwg_id]
        return httpx.Response(204)

    # -- instances --------------------------------------------------------

    def _create_instance(self, body: dict) -> httpx.Response:
        attach_vpc = body.get("attach_vpc") or []
        unknown_vpcs = [v for v in attach_vpc if v not in self.vpcs]
        if unknown_vpcs:
            return httpx.Response(400, json={"error": f"unknown VPC id(s): {unknown_vpcs}"})
        instance_id = f"instance-{next(self._instance_seq)}"
        instance = {
            "id": instance_id,
            "region": body["region"],
            "plan": body["plan"],
            "main_ip": "203.0.113.10",
            "status": "pending",
            "power_status": "stopped",
            "server_status": "none",
            "os_id": body.get("os_id", 0),
            "snapshot_id": body.get("snapshot_id", ""),
            "firewall_group_id": body.get("firewall_group_id", ""),
            "hostname": body.get("hostname", ""),
            "label": body.get("label", ""),
            "tags": body.get("tags", []),
            "date_created": "2026-09-26T00:00:00+00:00",
            "_vpc_id": attach_vpc[0] if attach_vpc else None,
            "_request_body": body,  # stashed for test assertions only, never sent back over real Vultr
        }
        self.instances[instance_id] = instance
        return httpx.Response(202, json={"instance": {k: v for k, v in instance.items() if not k.startswith("_")}})

    def _get_instance(self, instance_id: str) -> httpx.Response:
        instance = self.instances.get(instance_id)
        if instance is None:
            return httpx.Response(404, json={"error": "Instance not found"})
        return httpx.Response(200, json={"instance": {k: v for k, v in instance.items() if not k.startswith("_")}})

    def _delete_instance(self, instance_id: str) -> httpx.Response:
        if instance_id not in self.instances:
            return httpx.Response(404, json={"error": "Instance not found"})
        del self.instances[instance_id]
        return httpx.Response(204)

    def mark_active(self, instance_id: str) -> None:
        self.instances[instance_id]["status"] = "active"
        self.instances[instance_id]["power_status"] = "running"
        self.instances[instance_id]["server_status"] = "ok"
