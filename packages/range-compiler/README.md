# ghostrange-range-compiler

M5 Range Compiler + Fidelity Engine (Wave 1–2 foundation).

Entry: `ghostrange_range_compiler.pipeline.RangeCompiler`

Importers:

- Docker Compose (YAML)
- Terraform/OpenTofu (python-hcl2, not regex)
- Kubernetes (bounded YAML subset)

Does **not** call Vultr directly — emits `RangeSpecV2` / blueprint artifacts for `range-iac` + control plane.

## `intake` — GitHub repo as investigation input

`ghostrange_range_compiler.intake.analyze_repository(repository_url, branch)` is the
front door for the "repo + incident description is enough to start an investigation"
product direction (see `docs/architecture/PRODUCT.md`). It shallow-clones a **public**
GitHub repo into a temp dir (`github_fetch.py`, always cleaned up), walks the tree for
structural signals — compose files, Dockerfiles, Kubernetes manifests, Terraform,
package manifests, OpenAPI specs, `.env.example` files (`repo_scanner.py`) — and returns
a `ghostrange_contracts.derived_system_model.DerivedSystemModelV1`: a heuristic,
explicitly low-confidence candidate service inventory with per-fact provenance.

This sits **upstream of** `RangeCompiler`/`RangeSpecV2` above, not inside it — turning a
`DerivedSystemModelV1` into a buildable Range (this package's existing
compose/Terraform/K8s importers, sanitization, fidelity gates, etc.) is a separate,
not-yet-built integration step. Also explicitly out of scope for this pass: private
repos / GitHub App or OAuth auth, and full AST-level static analysis (this is
heuristic file/pattern matching only).

Consumed by `apps/api/ghostrange_api/investigation_routes.py` (`POST
/v1/investigations/intake`) and `apps/web/src/intake/` (the "Start an investigation"
screen, reachable at `/start`).
