# ADR-001: Monorepo Strategy

- **Status:** Accepted
- **Date:** 2026-09-26
- **Owner:** Agent 01 (Product Architect)
- **Formalizes:** `Decisions.md` #1 (locked by lead agent pre-research). This ADR documents *why* with more rigor; it does not reopen the choice.

## Context

GhostRange spans two languages by necessity: a Python backend/orchestration layer (`apps/api` + eight `packages/*` — `contracts`, `events`, `range-runtime`, `range-iac`, `vultr-control`, `execution-graph`, `scheduler`, `evidence`, `adversary-adapter`) and a TypeScript/React frontend (`apps/web`, `packages/ui-3d`). The project is being built by ~20 parallel agent workstreams over a fixed hackathon window (Milestone 1), most of which touch disjoint paths but several of which share contract types (`packages/contracts` → both backend consumers and hand-written frontend TS types) and must not diverge on tooling mid-build.

Two decisions had to be made together, because they interact: (a) whether to unify both languages under one monorepo *build orchestration tool*, and (b) whether that tool needs to be a heavyweight polyglot system (Nx, Turborepo, Bazel) or whether per-ecosystem native tooling (npm workspaces for JS/TS, `uv`/`pip` for Python) run side-by-side under one git root is sufficient.

Constraints specific to this project:
- Team is a small set of agents running concurrently, not a large org needing incremental-build caching across hundreds of packages.
- Time budget is the hackathon window — tooling setup and debugging (build graph misconfiguration, cache invalidation bugs) directly competes with feature time.
- No existing build-time pain yet: this is a *new* repo, so there is no evidence a caching/orchestration layer is needed. Optimizing for a problem that doesn't exist yet is premature.
- `packages/contracts` is the one place where the two ecosystems actually need to talk (Pydantic → JSON Schema → hand-checked TS types) — this is a schema-sync problem, not a build-graph problem, and no monorepo tool solves it for free anyway (see `Decisions.md` #3: no runtime codegen bridge yet, tracked as a follow-up).

## Decision

Single git repository, two independent, native per-ecosystem dependency managers, no cross-language build orchestrator for Milestone 1:

- **JavaScript/TypeScript side** (`apps/web`, `packages/ui-3d`): plain **npm workspaces**. A single root `package.json` with a `workspaces` field covering `apps/web` and `packages/ui-3d`; each package has its own `package.json`, own `tsconfig.json`, own build script. No shared build cache, no task graph tool.
- **Python side** (`apps/api` and the eight orchestration packages): **`uv`/`pip`** with each package as an installable local package (`pyproject.toml` per package), referenced via editable/path installs where cross-package imports are needed (e.g. `apps/api` depends on `packages/contracts`, `packages/events`).
- No Nx, Turborepo, Bazel, Pants, or other polyglot monorepo tool is introduced in Milestone 1.
- The two ecosystems are coordinated by convention (directory layout, this ADR, `Decisions.md`) and by the contract boundary in `packages/contracts`, not by tooling.

## Alternatives Considered

**Nx or Turborepo (polyglot-capable, but primarily JS-ecosystem-first task runners).**
Rejected for M1. Both add real value once the build graph is large enough that incremental/cached builds save meaningful time, or once task orchestration across many packages needs a dependency-aware `affected` command. At current scale (a handful of packages per language, first build of each), that value is close to zero and the cost is nonzero: another tool's config (`nx.json`/`turbo.json`) to get right under time pressure, another thing to debug when a build behaves unexpectedly, and — critically — neither tool natively unifies Python and TypeScript task graphs well; Python support in both is a bolt-on, which would mean *still* running two toolchains underneath while adding a third layer on top. Revisit at M2 if build/test iteration time becomes a measured bottleneck (explicitly flagged as a revisit trigger in `Decisions.md`).

**Bazel (or Pants) — true polyglot build system with fine-grained caching.**
Rejected. Bazel's value proposition is hermetic, cacheable, cross-language builds at scale; its cost is a steep setup curve (BUILD files per package, toolchain configuration for both Python and Node) that is disproportionate to a ~20-agent hackathon build. This is the kind of yak-shaving `Decisions.md` explicitly calls out avoiding for M1.

**Separate repositories (polyrepo) for `apps/web` vs. the Python side.**
Rejected. `packages/contracts` is the single source of truth for domain object schemas consumed by both sides (per `Decisions.md` #3); a polyrepo split would force either a published-package release cycle (versioning overhead the hackathon timeline can't absorb) or a git-submodule/subtree workaround (worse ergonomics than a monorepo for the same problem). Twenty parallel agents editing disjoint paths also benefits from one clone, one PR surface, one place to see cross-cutting state (`Progress.md`, `Decisions.md` at the root).

**Single language for everything (e.g., a Python-only frontend via Reflex/Streamlit, or a Node-only backend).**
Not seriously considered — the frontend requirement (React Three Fiber, per `Decisions.md` #5) and backend requirement (Python-native cyber-range/agent tooling ecosystem, per ADR-002) are both fixed by other decisions this ADR does not relitigate.

## Consequences

**Positive:**
- Zero new build-tool surface area to debug during the hackathon window.
- Each ecosystem uses the tooling its own community optimizes for (`npm` for JS/TS, `uv` for Python) — no impedance mismatch from forcing one tool to model both.
- Twenty agents can work in disjoint paths without contending over a shared build-graph config file.
- Easy to introduce Nx/Turborepo/Bazel later without an ecosystem migration — this ADR only defers the *orchestrator*, it doesn't preclude one.

**Negative / accepted debt:**
- No cross-language incremental build caching. A full rebuild is a full rebuild. Acceptable at current scale; will hurt if the package count or build time grows substantially — tracked as an M2 revisit trigger.
- No automated dependency graph for "what needs to rebuild when `packages/contracts` changes" — this is currently a human/process concern (documented in `Progress.md`'s wave plan: contracts-first, then dependents in parallel), not a tool-enforced one.
- Schema sync between Pydantic (`packages/contracts`) and hand-written frontend TS types is manual, checked against exported JSON Schema in CI rather than generated — this is a known, explicitly tracked follow-up (`Decisions.md` #3), not something this ADR's tooling choice fixes.
- Each package manages its own lockfile/venv; there's no single "install everything" command spanning both ecosystems (two commands: `npm install` at root for JS workspaces, per-package `uv sync`/`pip install -e` for Python packages). Acceptable overhead for the current team size.

**Revisit trigger:** build/test iteration time becomes a measured bottleneck, or package count grows enough that cross-language dependency tracking by convention breaks down (per `Decisions.md`, targeted at M2).
