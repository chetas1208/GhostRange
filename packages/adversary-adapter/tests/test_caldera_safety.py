import pytest

from ghostrange_adversary_adapter.caldera_client import CalderaConfig, CalderaRangeClient, CalderaSafetyError


def test_rejects_external_caldera_url():
    with pytest.raises(CalderaSafetyError):
        CalderaRangeClient(CalderaConfig(base_url="http://8.8.8.8:8888"))


def test_allows_localhost():
    CalderaRangeClient(CalderaConfig(base_url="http://127.0.0.1:8888"))
