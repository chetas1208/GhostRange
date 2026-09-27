from ghostrange_ghostwatch.authority import assert_not_forbidden_action
import pytest


@pytest.mark.parametrize("action", ["ArbitraryKubectlAction", "ProductionShellAction"])
def test_forbidden_actions(action: str):
    with pytest.raises(PermissionError):
        assert_not_forbidden_action(action)
