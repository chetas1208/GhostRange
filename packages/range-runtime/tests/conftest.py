from __future__ import annotations

import pytest
from ghostrange_contracts.enums import AssetRole
from ghostrange_contracts.range import AssetSpecV1, NetworkSpecV1, RangeSpecV1

from ghostrange_range_runtime.engine import RangeRuntimeEngine
from ghostrange_range_runtime.events import InMemoryEventSink
from ghostrange_range_runtime.persistence import SqliteTransitionStore
from ghostrange_range_runtime.provider import FakeComputeProvider


def make_spec(*, n_assets: int = 1) -> RangeSpecV1:
    net = NetworkSpecV1(name="corp-lan", cidr="10.0.0.0/24")
    assets = [
        AssetSpecV1(
            hostname=f"host-{i}",
            network_id=net.id,
            os_family="linux",
            role=AssetRole.SERVER,
            image="ubuntu-22.04",
        )
        for i in range(n_assets)
    ]
    return RangeSpecV1(
        name="ghostrange-auth-lab-v1",
        owner="chetasparekh2003@gmail.com",
        networks=[net],
        assets=assets,
    )


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "range_runtime.sqlite3"


@pytest.fixture
def store(db_path):
    s = SqliteTransitionStore(db_path)
    yield s
    s.close()


@pytest.fixture
def provider():
    return FakeComputeProvider()


@pytest.fixture
def sink():
    return InMemoryEventSink()


@pytest.fixture
def engine(store, provider, sink):
    return RangeRuntimeEngine(store=store, provider=provider, sink=sink)


@pytest.fixture
def spec():
    return make_spec()
