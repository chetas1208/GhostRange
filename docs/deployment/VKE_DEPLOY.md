# VKE Deploy Runbook -- GhostRange Control Plane

Status: manifests written and validated LOCALLY (no live cluster). This is the
deploy-when-ready path -- nothing in this document has been executed against a
real Vultr account. Creating a real VKE cluster is a new, billable cloud
resource and is explicitly held for the user's go-ahead, same discipline this
session applied to triggering the live M20 campaign and rotating API keys.
Do not run the "Create the cluster" section without that go-ahead.

Scope: this deploys GhostRange's **own control-plane services** (`api`, `web`,
`valkey`, `caddy` from `docker-compose.prod.yml`) to a real VKE cluster. It
does **not** touch range-asset provisioning (`packages/vultr-control`,
`packages/range-iac`) -- those stay on plain Vultr Compute per ADR-006 and
Decisions.md #11, unchanged. See `docs/research/VULTR.md` section 6 for the
capability research this runbook implements, and
`docs/architecture/ADR-006-vultr-integration.md` for why the two compute
populations (control plane vs. range assets) are treated differently.

## What's here

```
deploy/k8s/
  base/                       # api, web, valkey, caddy -- mirrors docker-compose.prod.yml
    namespace.yaml
    valkey-deployment.yaml, valkey-service.yaml
    api-configmap.yaml, api-deployment.yaml, api-service.yaml
    api-secret.example.yaml   # TEMPLATE ONLY -- not in kustomization resources, see its header
    web-deployment.yaml, web-service.yaml
    Caddyfile, caddy-deployment.yaml, caddy-service.yaml  # caddy IS the ingress, see below
    kustomization.yaml
  overlays/
    vke/                      # real-cluster overlay: registry images, real config values, 2 replicas
    local-kind/                # local validation overlay: local images, imagePullPolicy Never
```

## Design decisions this runbook assumes (with reasoning)

1. **Postgres and Object Storage stay external (Vultr Managed Postgres, Vultr
   Object Storage) -- nothing stateful moves in-cluster.**
   Why: Decisions.md #6 already locked Managed Postgres specifically to avoid
   running/patching a database by hand; `docker-compose.prod.yml`'s own header
   comment already says "no local Postgres" for the *current* Compute-VM
   deploy. Moving Postgres into VKE would mean re-adopting exactly the
   operational burden (backups, HA, patching, PVC/CSI capacity planning) that
   decision explicitly rejected, for a database that already has a working
   managed replacement wired via `POSTGRES_DSN`. Object Storage is the same
   argument: it is already S3-compatible, already the evidence-durability
   tier (Decisions.md #14, VULTR.md section 7), and an in-cluster object store
   (e.g. MinIO) would be a second, redundant blob store with no requirement
   pulling it in. Valkey is the one stateful-looking piece that DOES move
   in-cluster (see `valkey-deployment.yaml`) -- but only because it is
   configured with no persistence at all (`--save "" --appendonly no`,
   matching compose exactly): it's a pure pub/sub/cache layer, not a
   durability tier, so there is nothing for a PVC to protect.
2. **Plain Deployment, not Bitnami/official Helm subchart, for Valkey.**
   Why: this repo has zero Helm usage anywhere today (checked -- only prose
   mentions in docs, no `Chart.yaml` exists). A Bitnami Valkey/Redis subchart
   pulls in StatefulSet + PVC + replication/sentinel machinery designed for a
   *durable* Redis deployment; GhostRange's Valkey is deliberately ephemeral
   (see `docker-compose.prod.yml` line 1's comment: "no local Postgres" -- same
   ephemeral-by-design posture extends to Valkey, which has no volume even in
   compose). Adopting Helm for exactly one, trivial, single-container
   component would add a build tool this repo doesn't otherwise use for one
   `valkey-server --save "" --appendonly no` process -- not justified.
3. **Caddy is the ingress, not a separately-installed ingress-nginx
   controller.** Why: unlike its Cloud Controller Manager and CSI driver
   (installed automatically), VKE does not ship an ingress controller by
   default (see `docs/research/VULTR.md` section 6). Reusing the exact routing
   rules already proven in `deploy/caddy/Caddyfile` -- as a plain Deployment
   behind a `Service type=LoadBalancer` -- means there is exactly one place
   routing logic lives (not two configurations, Caddyfile + Ingress YAML, to
   keep in sync), and Vultr's Cloud Controller Manager provisions a real Load
   Balancer for that Service the same way it would for an ingress-nginx
   Service. See `deploy/k8s/base/caddy-deployment.yaml`'s header comment for
   the full reasoning.

## Local validation performed (real commands, real output)

Environment checked first: no `kind`/`k3d`/`minikube`/`helm`/`kubectl`/
`kustomize`/`kubeconform` were pre-installed. All were installed user-locally
(no sudo needed) via direct binary download to `~/.local/bin`:
`kubectl` v1.30.4, `kind` v0.24.0, `kustomize` v5.4.3, `k3d` v5.7.4,
`kubeconform` v0.6.7.

**Render (kustomize build), all three variants -- REAL, ran successfully:**

```
$ kustomize build deploy/k8s/base            # 11 resources, no errors
$ kustomize build deploy/k8s/overlays/vke     # 11 resources, no errors
$ kustomize build deploy/k8s/overlays/local-kind  # 11 resources, no errors
```

Verified the overlays actually take effect (not just "no error"): the `vke`
overlay's rendered output shows `image: REPLACE_WITH_REGISTRY/ghostrange-api:REPLACE_WITH_DEPLOY_SHA`,
`replicas: 2` on both `api` and `web`, and the merged ConfigMap literals
(`GHOSTRANGE_PUBLIC_URL: https://REPLACE_WITH_LB_IP.sslip.io`, etc.); the
`local-kind` overlay's rendered output shows `imagePullPolicy: Never` on both
containers. Kustomize's built-in name-reference rewriting was also confirmed
working: the caddy Deployment's volume correctly references the generated
`caddy-config-file-<hash>` ConfigMap name, not the unhashed name.

**Schema validation (kubeconform, offline, against real Kubernetes 1.30
OpenAPI schemas) -- REAL, ran successfully, strict mode (rejects unknown
fields too):**

```
$ kubeconform -strict -summary -kubernetes-version 1.30.0 <(kustomize build deploy/k8s/base)
Summary: 11 resources found in 1 file - Valid: 11, Invalid: 0, Errors: 0, Skipped: 0

$ kubeconform -strict -summary -kubernetes-version 1.30.0 <(kustomize build deploy/k8s/overlays/vke)
Summary: 11 resources found in 1 file - Valid: 11, Invalid: 0, Errors: 0, Skipped: 0

$ kubeconform -strict -summary -kubernetes-version 1.30.0 <(kustomize build deploy/k8s/overlays/local-kind)
Summary: 11 resources found in 1 file - Valid: 11, Invalid: 0, Errors: 0, Skipped: 0
```

**What was attempted and genuinely blocked -- a real local kind/k3d cluster
(the strongest possible proof, actually scheduling these pods):**

```
$ kind create cluster --name ghostrange-vke-test
ERROR: failed to create cluster: running kind with rootless provider requires
setting systemd property "Delegate=yes", see https://kind.sigs.k8s.io/docs/user/rootless/

$ k3d cluster create ghostrange-test --agents 0
ERRO Failed Cluster Start: ... node k3d-ghostrange-test-server-0 is running=true
in status=restarting
FATA Cluster creation FAILED, all changes have been rolled back!
```

Root cause (confirmed, not guessed): `docker info` shows this sandbox's Docker
daemon is rootless (`SecurityOptions: name=rootless`) and cgroup v2, but there
is **no systemd user session** (`systemctl --user` returns "Failed to connect
to bus: No medium found" -- no D-Bus). kind's own docs say rootless operation
needs `Delegate=yes` set via a systemd user unit, which requires a systemd
session to exist at all; k3d's server container failed for the same class of
reason (its control-plane container needs cgroup access kind/k3d normally get
via that delegation). This is a genuine sandbox limitation, not a manifest
problem -- the manifests themselves are proven schema-valid and internally
consistent by kubeconform + kustomize's build-time reference resolution above;
what's unproven is actual pod scheduling/health on a running kubelet, which
needs either this sandbox gaining a systemd session (out of my control) or a
cluster with cgroup delegation available (a real VKE cluster has this, since
Vultr's own node images are normal non-rootless VMs).

**NOT_RUN, and why, explicitly:** `kubectl apply --dry-run=client` was also
tried and does not work here either -- this version of kubectl fetches the
OpenAPI schema from a live API server even for client-side dry-run
(`dial tcp 127.0.0.1:8080: connect: connection refused` with no kubeconfig),
so it adds nothing beyond what kubeconform already validated against the same
real schema, offline. Actual pod-level behavior (does the api container pass
its readiness probe, does Caddy actually reach `api:8000`/`web:8080` by DNS,
does the Vultr CCM provision a real Load Balancer) is **NOT_RUN** -- it
requires either a working local cluster (blocked as above) or a real VKE
cluster (requires the go-ahead this document is gated behind).

## Create the cluster -- NOT EXECUTED, requires explicit go-ahead

### Recommended sizing

- **Region:** match wherever the control VM / Managed Postgres already live
  (the existing prod deploy is at a Vultr host reachable as `45.76.248.45`;
  confirm its region in the Vultr console -- likely `lax` given
  `VULTR_WORKER_REGION=lax` in `.env.production.example`, though that var is
  for range-asset *workers*, not necessarily the control host's own region --
  verify before creating the cluster, don't assume they match).
- **Node pool:** `vke-cpu-1c-2gb` (1 vCPU / 2GB, ~$10/mo, Vultr's own
  documented entry VKE plan) is too small once you add `kube-proxy`/CNI/CCM/
  CSI system pods on top of `api`+`web`+`valkey`+`caddy` -- recommend
  **`vc2-2c-4gb` (2 vCPU / 4GB) x 2 nodes** for a real deploy with the `vke`
  overlay's 2-replica api/web (rough cost: 2 times the 2c/4gb Cloud Compute
  rate, check current pricing at vultr.com/pricing before committing --
  control plane itself is free on VKE, you only pay for the node pool + the
  Load Balancer the `caddy` Service provisions + Block Storage if any is
  added later). A single `vke-cpu-1c-2gb` node is enough to prove the
  manifests schedule at all (`base/`, not `overlays/vke`, 1 replica each) if
  the goal is a cheap smoke test rather than a resilient deploy.
- **Kubernetes version:** pass whatever `vultr-cli kubernetes create --help`
  (or the Vultr console's cluster-create form) currently lists as latest
  stable at creation time -- do not hardcode a version here, Vultr's supported
  version list changes; verify at creation time.

### vultr-cli path (verified command syntax against Vultr's own CLI reference
docs, 2026-09-27 -- not executed)

```bash
# 1. Create the cluster (control plane free; only the node pool + LB + any
#    block storage bill). --high-avail adds a multi-replica control plane
#    (still no control-plane node cost, but recommended for anything beyond a
#    demo).
vultr-cli kubernetes create \
  --label "ghostrange-control" \
  --region <REGION> \
  --version <LATEST_STABLE_VERSION> \
  --node-pools "quantity:2,plan:vc2-2c-4gb,label:ghostrange-pool"

# 2. Fetch the kubeconfig once the cluster is ACTIVE (poll `vultr-cli
#    kubernetes get <cluster-id>` for status, or use the console)
vultr-cli kubernetes config <cluster-id> > ~/.kube/ghostrange-vke.yaml
export KUBECONFIG=~/.kube/ghostrange-vke.yaml
kubectl get nodes   # confirm nodes Ready before proceeding
```

### OpenTofu/Terraform path (per ADR-006: OpenTofu is the right IaC tool for
GhostRange's OWN infrastructure, as opposed to range-asset compilation which
bypasses OpenTofu -- this is exactly that "own infrastructure" case)

The Terraform/OpenTofu provider exposes `vultr_kubernetes` (cluster) and
`vultr_kubernetes_node_pools` (node pools) resources, mirroring the same
`region`/`version`/node-pool-plan fields as the CLI above. **NEEDS
VERIFICATION before use**: the exact current argument names/defaults for
these two resources -- the registry doc page renders client-side and this
research pass could not extract the field table directly (unlike
`vultr_instance`, which ADR-006 already verified in detail). Before writing
real `.tf`/`.tofu` files: run `tofu providers schema -json` against the
`vultr/vultr` provider (or open
`registry.terraform.io/providers/vultr/vultr/latest/docs/resources/kubernetes`
in a real browser) to confirm field names, then mirror the same
`region`/`plan`/`quantity` shape the vultr-cli command above already uses.
Do not hand-write those resource blocks from memory/guesswork given that gap.

## Deploy the manifests once the cluster exists and `kubectl get nodes` is Ready

```bash
# 1. Build and push real images (from repo root; registry of your choice --
#    ghcr.io, Vultr Container Registry, Docker Hub, etc.)
export REGISTRY=<your-registry>/<org>
export SHA=$(git rev-parse --short HEAD)
docker build -f deploy/docker/Dockerfile.api -t $REGISTRY/ghostrange-api:$SHA .
docker build -f deploy/docker/Dockerfile.web -t $REGISTRY/ghostrange-web:$SHA \
  --build-arg VITE_DATA_SOURCE=live --build-arg VITE_BOOTSTRAP_M20=false \
  --build-arg VITE_ENABLE_TOUR=false --build-arg VITE_API_BASE= .
docker push $REGISTRY/ghostrange-api:$SHA
docker push $REGISTRY/ghostrange-web:$SHA

# 2. Point the vke overlay at the real images/values (edit
#    deploy/k8s/overlays/vke/kustomization.yaml's REPLACE_WITH_* placeholders,
#    or use `kustomize edit set image` from that directory -- either way,
#    commit the edited overlay, never hand-edit rendered output)
cd deploy/k8s/overlays/vke
kustomize edit set image ghostrange-api:local=$REGISTRY/ghostrange-api:$SHA
kustomize edit set image ghostrange-web:local=$REGISTRY/ghostrange-web:$SHA

# 3. Create the real Secret BEFORE applying (see
#    deploy/k8s/base/api-secret.example.yaml's header for the exact command --
#    values come from the existing, gitignored .env.production, never
#    hand-typed into a new file)
kubectl create namespace ghostrange --dry-run=client -o yaml | kubectl apply -f -
kubectl create secret generic ghostrange-api-secrets -n ghostrange \
  --from-literal=POSTGRES_DSN="$POSTGRES_DSN" \
  --from-literal=S3_ACCESS_KEY_ID="$S3_ACCESS_KEY_ID" \
  --from-literal=S3_SECRET_ACCESS_KEY="$S3_SECRET_ACCESS_KEY" \
  --from-literal=VULTR_INFERENCE_API_KEY="$VULTR_INFERENCE_API_KEY" \
  --from-literal=VULTR_API_KEY="$VULTR_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

# 4. Apply
kubectl apply -k deploy/k8s/overlays/vke

# 5. Wait for the LoadBalancer IP (Vultr CCM provisions a real Vultr Load
#    Balancer here -- this takes a few minutes)
kubectl -n ghostrange get svc caddy -w
#   ... EXTERNAL-IP transitions from <pending> to a real IP.

# 6. Point DNS at it: same sslip.io/nip.io pattern already used for the
#    Compute VM (deploy/caddy/Caddyfile's own comment shows this convention),
#    or a real domain's A record if you have one. Then update the Caddyfile
#    ConfigMap to add TLS for that hostname and roll caddy:
LB_IP=$(kubectl -n ghostrange get svc caddy -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
#   Edit deploy/k8s/base/Caddyfile: change `:80 { ... }` to
#   `${LB_IP}.sslip.io, :443 { ... }` (same site-block shape as
#   deploy/caddy/Caddyfile already uses for the Compute VM's IP) -- Caddy's
#   automatic HTTPS then issues a real Let's Encrypt cert for that sslip.io
#   name on first request.
kubectl apply -k deploy/k8s/overlays/vke   # re-applies the updated ConfigMap
kubectl -n ghostrange rollout restart deployment/caddy

# 7. Verify
curl https://${LB_IP}.sslip.io/health/live
curl https://${LB_IP}.sslip.io/          # -> web
```

## Local validation path (for whenever this sandbox, or a different one, has
working kind/k3d/minikube)

```bash
docker build -f deploy/docker/Dockerfile.api -t ghostrange-api:local .
docker build -f deploy/docker/Dockerfile.web -t ghostrange-web:local .
kind create cluster --name ghostrange-local
kind load docker-image ghostrange-api:local ghostrange-web:local --name ghostrange-local
# real secrets not needed for a local smoke test -- use throwaway values:
kubectl create namespace ghostrange
kubectl create secret generic ghostrange-api-secrets -n ghostrange \
  --from-literal=POSTGRES_DSN="postgresql://x:x@localhost:5432/x" \
  --from-literal=S3_ACCESS_KEY_ID="x" --from-literal=S3_SECRET_ACCESS_KEY="x" \
  --from-literal=VULTR_INFERENCE_API_KEY="x" --from-literal=VULTR_API_KEY="x"
kubectl apply -k deploy/k8s/overlays/local-kind
kubectl -n ghostrange get pods -w
```
(This is the exact path this session tried and was blocked on -- see "Local
validation performed" above. It should work in any environment where `kind
create cluster` itself succeeds.)
