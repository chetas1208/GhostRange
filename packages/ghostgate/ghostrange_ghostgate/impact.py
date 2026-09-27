"""Blast radius from component graph (M6-style impact summary)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BlastRadiusV1:
    direct: list[str] = field(default_factory=list)
    downstream: list[str] = field(default_factory=list)
    indirect: list[str] = field(default_factory=list)


# Auth-lab reference edges — not production topology.
_AUTH_LAB_EDGES: dict[str, list[str]] = {
    "auth-service": ["api-gateway"],
    "api-gateway": ["web-frontend"],
}


def compute_blast_radius(changed: list[str]) -> BlastRadiusV1:
    direct = list(changed)
    downstream: list[str] = []
    indirect: list[str] = []
    seen = set(direct)
    for c in direct:
        for nxt in _AUTH_LAB_EDGES.get(c, []):
            if nxt not in seen:
                downstream.append(nxt)
                seen.add(nxt)
    for d in downstream:
        for nxt in _AUTH_LAB_EDGES.get(d, []):
            if nxt not in seen:
                indirect.append(nxt)
                seen.add(nxt)
    return BlastRadiusV1(direct=direct, downstream=downstream, indirect=indirect)


def all_affected(br: BlastRadiusV1) -> list[str]:
    return br.direct + br.downstream + br.indirect
