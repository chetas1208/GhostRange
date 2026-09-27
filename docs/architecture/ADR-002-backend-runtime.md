# ADR-002: Backend Language & Runtime

- **Status:** Accepted
- **Date:** 2026-09-26
- **Owner:** Agent 01 (Product Architect)
- **Formalizes:** `Decisions.md` #2 (locked by lead agent pre-research). This ADR documents *why* with more rigor; it does not reopen the choice.

## Context

`apps/api` and every orchestration package (`packages/contracts`, `range-runtime`, `scheduler`, `evidence`, `vultr-control`, `adversary-adapter`, `execution-graph`) need a single backend language. This layer's job, per `docs/architecture/PRODUCT.md` §4, is: compile a `RangeSpec` into live infra via Vultr, drive a `Task` DAG (`execution-graph`) with a hard safety boundary, run GhostScheduler's decisions, adapt to MITRE CALDERA for adversary emulation, and maintain append-only evidence/provenance. None of this is CPU-bound numerical computation; nearly all of it is I/O-bound orchestration (HTTP calls to Vultr's API, CALDERA's REST API, Postgres, Redis/Valkey) plus a meaningful amount of "glue" — invoking LLM-driven agents, shaping their structured outputs into the domain objects in `PRODUCT.md` §2, and enforcing policy checks around them.

Two prior-art facts matter directly:
- **CALDERA** (adopted per `Decisions.md` #8 as the adversary emulation engine, accessed via `packages/adversary-adapter`) is itself a Python application with a Python plugin ecosystem (including Atomic Red Team integrations). Talking to it, and to the broader cyber-range/agent-research ecosystem this project draws on, is lower-friction in Python — REST adapters aside, community tooling, sample abilities, and parsers in this space are overwhelmingly Python-first.
- **Contracts are the integration seam** (`Decisions.md` #3): Pydantic v2 models in `packages/contracts` are the single authoritative schema for every domain object, exported to JSON Schema for the frontend to check against. Keeping every orchestration package in the same language as `packages/contracts` means every consumer imports the *actual* Pydantic classes directly — no serialization boundary, no second type system to keep in sync, no codegen step required to get validated types into `range-runtime`, `scheduler`, `evidence`, etc.

## Decision

**Python 3.11+ with FastAPI** for `apps/api`, and plain Python (importing `packages/contracts` directly, no web framework needed) for the non-HTTP orchestration packages (`range-runtime`, `scheduler`, `evidence`, `vultr-control`, `adversary-adapter`, `execution-graph`).

- FastAPI is used specifically where an HTTP/WebSocket surface is needed: `apps/api`'s REST endpoints and the event-sync gateway (see ADR-011).
- Async I/O (`async`/`await`, `httpx` or similar for outbound calls to Vultr/CALDERA) is the default execution model for this layer, since the workload is I/O-bound orchestration, not CPU-bound compute.
- Python 3.11+ specifically for its interpreter-level performance improvements over 3.9/3.10 (relevant given async orchestration under load) and because it's the version where structural pattern matching and modern typing features (needed for clean Pydantic v2 models with discriminated unions across the state-machine-heavy domain model in `PRODUCT.md`) are mature.

## Alternatives Considered

**Go, for the control plane.**
Considered specifically for `packages/execution-graph` and `packages/scheduler` — Go's goroutines/channels are a genuinely better fit for a DAG scheduler's concurrency shape than Python's async model or its GIL-constrained threads. Rejected for M1 for one decisive reason: it would split `packages/contracts` across two type systems with no codegen bridge yet (per `Decisions.md` #2). Every domain object in `PRODUCT.md` §2 would need to exist as both a Pydantic model and a Go struct, hand-kept in sync, doubling the surface area for schema drift during a hackathon build where the schema itself is still being iterated on by Agent 14. The concurrency-primitive advantage doesn't outweigh that cost at M1's scale (single-digit concurrent `World`s, not thousands). **Explicitly flagged for revisit**: if `packages/range-runtime`'s hot path (many concurrent `ComputeWorker`s, high-frequency `Task` dispatch) becomes Python-perf-bound, extracting just that hot path to Go behind a narrow RPC/queue boundary is the fallback — not a full-stack rewrite.

**Node.js/TypeScript backend (one language across the whole stack).**
Rejected. The strongest argument for it is eliminating the two-language split entirely (one type system, shared with `apps/web`). It loses on the concrete integration need: CALDERA and the surrounding cyber-range/red-team tooling ecosystem (Atomic Red Team parsers, ATT&CK data libraries, the broader corpus Agent 02/03's research draws on) is Python-native. Building `packages/adversary-adapter` and the eventual IaC/cloud-init generation in `packages/range-iac` against that ecosystem from Node would mean either shelling out to Python anyway (getting the worst of both: two languages *and* a subprocess boundary) or reimplementing integrations that already exist in Python. Not worth it for a single shared type system, especially since the JSON-Schema-checked-in-CI approach (`Decisions.md` #3) already gives a manual but workable bridge.

**Rust, for performance and memory safety in the execution boundary specifically.**
Rejected for M1. The safety boundary in `packages/execution-graph` (per `Decisions.md` #9) needs to be *architecturally* correct (an allowlist check that cannot be bypassed by a compromised agent) far more than it needs to be *memory-safe at the language level* — the threat model is a misbehaving LLM agent issuing an out-of-scope action request, not a buffer overflow. Rust's tooling/ecosystem maturity for the Vultr/CALDERA integration surface is also weaker than Python's. Same "two type systems" cost as Go applies, with a steeper learning-curve tax under hackathon time pressure.

**Django (instead of FastAPI) for `apps/api`.**
Not seriously considered. Django's batteries (ORM, admin panel, templating) solve problems GhostRange doesn't have at this layer — `apps/api` is a thin orchestration/event-gateway surface over Pydantic-modeled domain objects and an async event pipeline (ADR-011), not a CRUD-heavy server-rendered app. FastAPI's native Pydantic integration (same v2 models as `packages/contracts`, zero translation) and first-class async support are direct fits; Django would add its own ORM's model layer as a second, redundant representation of the same domain objects.

## Consequences

**Positive:**
- One language for the entire backend means `packages/contracts`' Pydantic models are imported, not re-serialized, by every consumer package — no schema-sync tax on the backend side (the only remaining schema-sync tax is backend-Python ↔ frontend-TypeScript, which is out of scope for this ADR and addressed by `Decisions.md` #3's JSON-Schema-in-CI approach).
- Directly leverages the existing Python-native cyber-range/adversary-emulation ecosystem (CALDERA, Atomic Red Team) rather than fighting it.
- FastAPI + Pydantic v2 gives request/response validation "for free" against the same models used internally — fewer hand-written validators at the API boundary.
- Async-first fits the actual workload (I/O-bound calls to Vultr, CALDERA, Postgres, Redis/Valkey) better than a synchronous/threaded model would.

**Negative / accepted debt:**
- Python's GIL means CPU-bound work (should any emerge — e.g. heavy evidence-diffing or local model inference) can't scale via threads within one process; would need multiprocessing or offloading to a `ComputeWorker`, not something this ADR solves today.
- No compile-time type checking across the whole backend the way Go or Rust would give — Python's typing is enforced by Pydantic at runtime boundaries and by `mypy`/IDE tooling at dev time, which is weaker than a compiler guarantee. Given the domain model in `PRODUCT.md` is state-machine-heavy (many enums, many invariants), this is a real gap partially mitigated by Pydantic v2's stricter validation and discriminated unions, but worth naming.
- If `packages/range-runtime` or `packages/scheduler` become throughput-bound under real concurrent-`World` load, the Python choice will need the Go-extraction fallback described above — this is accepted now as a known, bounded, revisit-able risk rather than solved preemptively.

**Revisit trigger:** measured throughput/latency problems in `range-runtime`'s or `scheduler`'s hot path that async I/O tuning doesn't resolve — at that point, extract the specific hot path behind an RPC/queue boundary rather than reopening this ADR wholesale.
