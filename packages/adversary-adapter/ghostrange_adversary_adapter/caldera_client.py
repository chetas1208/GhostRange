"""Caldera REST adapter — targets range-local base URL only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx


class CalderaSafetyError(ValueError):
    pass


@dataclass(frozen=True)
class CalderaConfig:
    base_url: str
    api_key: str = ""
    timeout_sec: float = 30.0


def _assert_range_local(base_url: str) -> None:
    parsed = urlparse(base_url)
    host = (parsed.hostname or "").lower()
    if host in ("localhost", "127.0.0.1"):
        return
    if host.endswith(".ghostrange.local") or host.startswith("10.") or host.startswith("192.168."):
        return
    raise CalderaSafetyError(f"Caldera base_url must be range-local, got {host!r}")


class CalderaRangeClient:
    def __init__(self, config: CalderaConfig) -> None:
        _assert_range_local(config.base_url)
        self.config = config

    async def list_abilities(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(base_url=self.config.base_url, timeout=self.config.timeout_sec) as client:
            r = await client.get("/api/v2/abilities")
            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, list) else []

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(base_url=self.config.base_url, timeout=5.0) as client:
                r = await client.get("/api/v2/health")
                return r.status_code == 200
        except httpx.HTTPError:
            return False


__all__ = ["CalderaRangeClient", "CalderaConfig", "CalderaSafetyError"]
