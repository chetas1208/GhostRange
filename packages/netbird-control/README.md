# ghostrange-netbird-control

The single choke point for every call GhostRange makes to the [NetBird](https://netbird.io)
management API. NetBird is a WireGuard-based identity-aware mesh overlay GhostRange uses for
control-plane <-> worker connectivity, ephemeral worker enrollment (setup keys), and
micro-segmentation (policy groups) — it sits *alongside* Vultr VPC (cloud-local L2/L3 network)
and GhostShield (action authorization), and does not replace either.

This package only wraps the small slice of the NetBird API GhostRange actually needs:

- **`NetBirdClient.find_peer_by_name(name)`** — look up a peer by its NetBird name/hostname
  (workers enroll with a deterministic hostname, e.g. `gr-worker-<suffix>`, so this is how the
  worker readiness gate finds "its" peer without needing NetBird's own peer id).
- **`NetBirdClient.is_peer_ready(peer, group=...)`** — a peer is "ready" once it is
  `connected` to the management server **and** a member of the required policy group
  (default `ghostrange-workers`, see `NETBIRD_WORKER_GROUP`). Micro-segmentation only works if
  every worker actually lands in the right group — this is why group membership, not just
  connectivity, gates readiness.
- **`NetBirdClient.list_groups()`** — list policy groups (used to verify a group exists / for
  diagnostics; also the one read-only call safe to run against a real account to confirm an API
  token authenticates).
- **`NetBirdClient.revoke_peer(peer_id)`** — delete a peer from the mesh. Called when a worker
  is torn down, alongside the existing Vultr VM termination, so a destroyed worker's mesh
  identity does not linger.
- **`NetBirdClient.create_setup_key(...)`** — optional: mint a fresh setup key server-side
  (e.g. a one-off key auto-assigned to `ghostrange-workers`) instead of reusing the static
  `NETBIRD_WORKER_SETUP_KEY`. Not wired into the default provisioning path yet; available for
  a future per-worker-ephemeral-key upgrade.

```python
from ghostrange_netbird_control import NetBirdClient

client = NetBirdClient(api_token=os.environ["NETBIRD_API_TOKEN"])  # base_url defaults to https://api.netbird.io
peer = client.find_peer_by_name("gr-worker-ab12cd34")
if peer and client.is_peer_ready(peer, group="ghostrange-workers"):
    ...  # promote worker to READY
```

Authentication is a static bearer-style token: every request carries
`Authorization: Token <NETBIRD_API_TOKEN>` (NetBird's own convention — note this is `Token`,
not `Bearer`, unlike the Vultr client in `packages/vultr-control`). The token is read from the
environment (or passed explicitly) and never logged, never placed in an exception message, and
never returned in any record.

Two implementations of one interface, mirroring `packages/vultr-control`'s pattern:

- **`NetBirdClient`** — calls the real API (`https://api.netbird.io` by default; a self-hosted
  NetBird management server's URL also works via `base_url=`).
- **`FakeNetBirdTransport`** (in `tests/`) — an `httpx.MockTransport`-based fake used by every
  test in this package and importable by callers (e.g. `apps/api`'s tests) that want to
  exercise the readiness gate without a real NetBird account.

No live NetBird calls are made in this package's own test suite. The one exception carved out
by the integration task this package was built for: a single read-only `list_groups()` call
against the real account, to confirm `NETBIRD_API_TOKEN` authenticates — never anything
mutating (no group/policy/setup-key creation or deletion against the real account from tests).
