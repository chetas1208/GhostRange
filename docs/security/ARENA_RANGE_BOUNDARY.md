# Arena range boundary

All security scenarios run against **owned, isolated, disposable** GhostRange environments. No external offensive targets.

Live Vultr (when enabled):

- `M19_LIVE_ARENA_MAX_USD` cap
- Default max 2 workers, no GPU unless `ALLOW_M19_LIVE_GPU=true`
- Cleanup invariant: `owned_workers == []`

**Current status:** `LIVE_ARENA_NOT_RUN` (Vultr API ACL blocked on control VM).
