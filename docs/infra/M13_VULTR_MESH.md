# M13 Vultr Federation (Agent 32)

**Status: LIVE_MESH_NOT_RUN**

Planned layout (when credentials authorized):

- 3× isolated compute instances, separate VPCs
- Per-node PostgreSQL or embedded DB — **no cross-VPC DB**
- Object storage for **content-addressed Mesh artifacts only** (no raw evidence)
- Mesh coordinator on dedicated small instance

Cost tracking: compute + egress + storage (TODO when live).

M13 proof uses `GhostMeshHarness` (5 logical nodes) instead.
