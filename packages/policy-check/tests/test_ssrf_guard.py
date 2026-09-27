from __future__ import annotations

import pytest

from ghostrange_policy_check import SSRFBlockedError, assert_safe_egress_url, is_blocked_address
from ghostrange_policy_check.ssrf_guard import VULTR_METADATA_HOST


def test_metadata_endpoint_is_blocked():
    assert is_blocked_address(VULTR_METADATA_HOST) is True


@pytest.mark.parametrize(
    "ip",
    ["169.254.169.254", "127.0.0.1", "10.0.0.5", "172.16.5.5", "192.168.1.1", "::1", "fe80::1"],
)
def test_private_and_link_local_addresses_are_blocked(ip):
    assert is_blocked_address(ip) is True


@pytest.mark.parametrize("ip", ["8.8.8.8", "1.1.1.1", "93.184.216.34"])
def test_public_addresses_are_not_blocked(ip):
    assert is_blocked_address(ip) is False


def test_unparseable_address_fails_closed():
    assert is_blocked_address("not-an-ip") is True


def test_assert_safe_egress_url_blocks_metadata_url():
    with pytest.raises(SSRFBlockedError):
        assert_safe_egress_url(f"http://{VULTR_METADATA_HOST}/v1/")


def test_assert_safe_egress_url_blocks_host_outside_allowlist():
    with pytest.raises(SSRFBlockedError):
        assert_safe_egress_url(
            "https://8.8.8.8/steal", allowed_hosts=frozenset({"evidence.ghostrange.internal"})
        )


def test_assert_safe_egress_url_rejects_url_with_no_host():
    with pytest.raises(SSRFBlockedError):
        assert_safe_egress_url("not a url at all")
