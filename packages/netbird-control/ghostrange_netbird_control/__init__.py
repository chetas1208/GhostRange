"""ghostrange-netbird-control: the single choke point for GhostRange's calls
to the NetBird management API.

Public surface:

    from ghostrange_netbird_control import (
        NetBirdClient,
        Peer, Group, SetupKey,
    )
    from ghostrange_netbird_control.errors import NetBirdControlError, ...

See README.md for the exact NetBird endpoints ``NetBirdClient`` calls and
how to supply real credentials.
"""

from .client import NetBirdClient
from .errors import (
    NetBirdAuthError,
    NetBirdControlError,
    NetBirdNotFoundError,
    NetBirdRateLimitedError,
    NetBirdServerError,
    NetBirdTimeoutError,
    NetBirdUnavailableError,
    NetBirdValidationError,
)
from .http_client import DEFAULT_BASE_URL, NetBirdHTTPClient
from .models import Group, Peer, PeerGroupRef, SetupKey

__all__ = [
    "NetBirdClient",
    "NetBirdHTTPClient",
    "DEFAULT_BASE_URL",
    "Peer",
    "PeerGroupRef",
    "Group",
    "SetupKey",
    "NetBirdControlError",
    "NetBirdAuthError",
    "NetBirdNotFoundError",
    "NetBirdValidationError",
    "NetBirdRateLimitedError",
    "NetBirdServerError",
    "NetBirdUnavailableError",
    "NetBirdTimeoutError",
]
