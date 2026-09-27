"""Fixtures for the event persistence layer tests
(``packages/events/ghostrange_events/store``).

These tests require a real, running Postgres + Redis/Valkey — see
``docker-compose.dev.yml`` at the repo root:

    docker compose -f docker-compose.dev.yml up -d --wait

Connection info defaults to that compose file's exposed ports; override via
``POSTGRES_DSN`` / ``REDIS_URL`` env vars (see ``.env.dev.example``) to
point at a different instance.

Honesty note: if neither service is reachable, every test in this
directory is skipped (not silently passed, not faked) with a clear reason
— see ``_require_store_infra`` below.
"""

from __future__ import annotations

import os
import uuid

import psycopg
import pytest
import pytest_asyncio
import redis.asyncio as redis_asyncio

from ghostrange_events.store import EventGateway, PostgresEventStore, RedisBus

DEFAULT_POSTGRES_DSN = "postgresql://ghostrange:ghostrange@localhost:5432/ghostrange"
DEFAULT_REDIS_URL = "redis://localhost:6379/0"

POSTGRES_DSN = os.environ.get("POSTGRES_DSN", DEFAULT_POSTGRES_DSN)
REDIS_URL = os.environ.get("REDIS_URL", DEFAULT_REDIS_URL)


def _infra_reachable() -> tuple[bool, str]:
    try:
        conn = psycopg.connect(POSTGRES_DSN, connect_timeout=3)
        conn.execute("SELECT 1")
        conn.close()
    except Exception as exc:  # noqa: BLE001 - report exact reason in skip
        return False, f"Postgres unreachable at {POSTGRES_DSN}: {exc}"

    try:
        import redis as redis_sync

        client = redis_sync.Redis.from_url(REDIS_URL, socket_connect_timeout=3)
        client.ping()
        client.close()
    except Exception as exc:  # noqa: BLE001
        return False, f"Redis/Valkey unreachable at {REDIS_URL}: {exc}"

    return True, ""


_REACHABLE, _SKIP_REASON = _infra_reachable()

requires_store_infra = pytest.mark.skipif(not _REACHABLE, reason=_SKIP_REASON)


@pytest_asyncio.fixture
async def pg_store():
    store = await PostgresEventStore.connect(POSTGRES_DSN)
    yield store
    await store.close()


@pytest_asyncio.fixture
async def redis_bus():
    bus = await RedisBus.connect(REDIS_URL)
    yield bus
    await bus.close()


@pytest_asyncio.fixture
async def gateway(pg_store, redis_bus):
    return EventGateway(pg_store, redis_bus)


@pytest.fixture
def range_id() -> uuid.UUID:
    """A fresh random Range id per test — this is what keeps tests
    isolated from each other without needing to truncate shared tables:
    ``event_log``/``range_seq_counters`` are keyed by ``range_id``, so two
    tests never see each other's rows or seq counters.
    """
    return uuid.uuid4()
