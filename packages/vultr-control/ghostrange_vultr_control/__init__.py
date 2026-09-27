"""ghostrange-vultr-control: the single choke point for all Vultr API calls.

Public surface:

    from ghostrange_vultr_control import (
        VultrControlProvider,   # the interface both implementations honor
        RealVultrProvider,      # live Vultr API v2, reads VULTR_API_KEY
        MockVultrProvider,      # deterministic in-memory fake, provider="mock"
        CreateWorldRequest, CreateComputeRequest,
        WorldRecord, ComputeRecord,
        GhostRangeTags, ProviderKind, ResourceStatus,
    )
    from ghostrange_vultr_control.errors import VultrControlError, ...

See README.md for the exact Vultr endpoints RealVultrProvider calls, how to
supply real credentials, and the current interface-stability contract for
``packages/range-runtime`` / ``packages/range-iac``.
"""

from .errors import (
    VultrAuthError,
    VultrConflictError,
    VultrControlError,
    VultrNotFoundError,
    VultrRateLimitedError,
    VultrServerError,
    VultrTimeoutError,
    VultrUnavailableError,
    VultrValidationError,
)
from .interface import VultrControlProvider
from .mock_provider import MockVultrProvider
from .models import (
    ComputeRecord,
    CreateComputeRequest,
    CreateWorldRequest,
    GhostRangeTags,
    ProviderKind,
    ResourceStatus,
    WorldRecord,
)
from .real_provider import RealVultrProvider

__all__ = [
    "VultrControlProvider",
    "RealVultrProvider",
    "MockVultrProvider",
    "CreateWorldRequest",
    "CreateComputeRequest",
    "WorldRecord",
    "ComputeRecord",
    "GhostRangeTags",
    "ProviderKind",
    "ResourceStatus",
    "VultrControlError",
    "VultrAuthError",
    "VultrNotFoundError",
    "VultrValidationError",
    "VultrConflictError",
    "VultrRateLimitedError",
    "VultrServerError",
    "VultrUnavailableError",
    "VultrTimeoutError",
]
