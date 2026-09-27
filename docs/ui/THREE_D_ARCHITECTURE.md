# GhostRange 3D Architecture (M1)

Author: Agent 16 (3D Systems Architect). Status: design doc for implementation — a
separate wave (Agents 17/18/19) builds against this directly.

**Contracts note:** `packages/contracts` and `packages/events` are empty at the time
of writing (Batch D, which owns them, had not landed). The domain shapes referenced
below (`World`, `MachineEntity`, `Task`, `ComputeWorker`, `SchedulerDecision`,
`Evidence`, `Verification`, `AgentRecord`, `AttackEvent`) are this doc's *proposed*
minimal fields, inferred from Decisions.md, the event catalog given in the brief, and
the product spaces (Multiverse/Execution/Evidence). When Batch D's Pydantic models
land, reconcile field names against this doc via an ADR addendum rather than silent
drift — the store shape in this doc is written so a rename is a type-level fix, not
a structural one (single normalization layer, see "State Architecture").

---

## 1. Why React Three Fiber (not raw Three.js, not a heavier engine)

**Against raw Three.js.** GhostRange's hard rule is that domain state lives in
Zustand and 3D objects are derived/pure. Raw Three.js gives no reconciler — every
add/remove/update of a mesh in response to a backend event has to be hand-written
imperative scene-graph surgery (`scene.add`, `scene.remove`, manual disposal). That
imperative surface is exactly where engineers get tempted to stash a "just this one"
piece of domain state on an `Object3D.userData` for convenience, which is precisely
the anti-pattern the hard rule forbids. R3F's declarative model (`{worlds.map(w =>
<RangeWorld key={w.id} world={w} />)}`) makes "materialize only after the event
arrives" the *default* behavior of a list-render, not something to remember to
implement — a world absent from the `worlds` array is a world absent from the scene,
full stop. This is also why WorldFork/WorldCollapse (mount/unmount animations) are
naturally expressible as component lifecycle rather than manual scene diffing.

**Against a heavier engine (Babylon.js, PlayCanvas, a Unity/Unreal WebGL export).**
These bring a full editor/asset pipeline, larger baseline bundle (Babylon's core is
roughly 2-3x three.js's ~600KB before any helpers), scene-graph object overhead
tuned for imported-asset-heavy games, and in Unity/Unreal's case a completely
separate toolchain outside the locked Vite/React/TS stack. GhostRange explicitly
wants *no* downloaded 3D assets and *no* physics engine — the exact features those
engines are optimized around. None of them has an R3F-equivalent first-class React
reconciler; bolting React onto them means re-deriving what R3F already solved.
Three.js itself (via R3F) is the right *rendering* layer: it's the lowest-overhead
option that still gives WebGL2 (and an optional WebGPU path, see §2), and R3F is the
highest-adoption, best-maintained React binding for it, with drei providing 100+
composable helpers so we import only what we use (`Decisions.md` already commits to
"drei (selective)").

**Net effect on this doc's design:** every primitive below is a plain React
component whose entire visual state is a pure function of props derived from the
store. None of them hold domain state in a `ref` or in Three.js object properties
except transient, non-domain animation state (current tween progress, particle
positions) — see the per-primitive sections and the hard-rule callout in §4.

---

## 2. WebGPU vs WebGL: target WebGL2 only for M1

**Recommendation: do not target WebGPU in M1.** Use R3F's default WebGL2 renderer
unmodified. Revisit at M2 only if a specific feature needs a compute shader.

Reasoning:
- **Nothing in the M1 scene needs it.** WebGPU's real advantage over WebGL2 is
  compute shaders and lower CPU driver overhead at very high draw-call counts. M1's
  perf budget explicitly caps particle counts (CostParticle, ThreatPulse) and relies
  on instancing (ComputeNode, ExecutionTask, EvidenceArtifact, VerificationRing) to
  stay in the low thousands of draw calls at most — comfortably within WebGL2/instancing
  territory on an ordinary laptop GPU.
- **Ecosystem risk.** R3F can swap in Three.js's `WebGPURenderer` via the `gl` prop,
  but a meaningful slice of drei's helpers and third-party materials still assume
  WebGL-specific extensions/uniform conventions; treating WebGPU as first-class
  today means auditing every drei helper we use for compatibility — pure yak-shaving
  for a hackathon milestone, the exact thing Decisions.md item 1 tells us to avoid.
- **Fallback cost if we chose WebGPU first.** Going WebGPU-first and falling back to
  WebGL is strictly worse than going WebGL-first and upgrading later, because it
  means writing two code paths from day one. Going WebGL-first defers that cost
  until (if) it's actually needed.
- **Concrete guard for later:** isolate renderer construction in one file,
  `packages/ui-3d/src/renderer.ts`, exporting a `createRenderer(canvas)` that R3F's
  `<Canvas gl={createRenderer}>` consumes. If M2 introduces a GPGPU-shaped need
  (e.g., a large-N particle field simulated on the GPU instead of capped/instanced),
  swapping this one file to construct a `WebGPURenderer` with a WebGL2 fallback
  check is a contained change, not a rewrite.

---

## 3. Component Primitives (20)

All 20 live in `packages/ui-3d/src/components/<Name>.tsx` as a shared library
consumed by `apps/web`'s three space-specific scenes (Multiverse/Execution/Evidence),
per the "independently coded, not one giant Scene.tsx" requirement. Each owns its
own geometry, animation (`useFrame`), pointer interaction, prop-to-material mapping,
and — where noted — instancing/LOD strategy. None subscribes to the Zustand store
directly except via the selector hooks described in §4; each receives its domain
data as props from a thin "container" usage in the relevant space Scene, keeping the
primitives themselves storage-agnostic and testable in isolation (e.g., with
Storybook or plain unit tests feeding fixed props).

### RangeWorld
Renders one World node in the Multiverse view: a small procedural icosphere shell
with an inner glow, plus a status chip (drei `<Billboard>` + `<Text>`, not `<Html>`,
so it survives the same LOD/instancing pipeline as the rest of the scene). Props:
`{ id, label: 'A'|'B'|'C', status, parentWorldId, position }` from the proposed
`World` entity, where `position` comes from a tree/force-layout selector, not from
anything stored in Three.js. Appears (as a `ProvisioningGhost`-styled variant) on
`world.requested`; solidifies its material on `world.ready`; participates in a
`WorldFork` intro animation on `world.forked`; plays a `WorldCollapse` animation and
is removed from the store (see §5) on `world.destroyed`. Not instanced — world count
per investigation is small (a handful); a per-status material lookup table is cheap
enough on its own.

### NetworkNode
Renders one topology machine (Gateway/API/Auth/DB) inside an opened World's scene.
Props from the proposed `MachineEntity`: `{ id, worldId, role, status, position }`,
where `position` is a fixed per-role layout slot computed once per world. Each role
gets a distinct cheap procedural primitive (box=Gateway, capsule=API, cone=Auth,
cylinder=DB) so roles are visually identifiable without textures. **Appears only
once the backing machine is actually `READY`** (`compute.ready` for that machine id)
— while `REQUESTED`/`PROVISIONING` it renders the shared `ProvisioningGhost` variant
instead of a solid node, which is the concrete mechanism enforcing "never invent
successful infra state ahead of reality." Removed on `compute.released`. Not
instanced (≤10s of machines per world); uses drei `<Detailed>` to drop segment count
on distant/many-worlds-visible camera states.

### ComputeNode
Renders one Execution-space compute worker (CPU/GPU/serverless) in the Scheduler
view. Props from the proposed `ComputeWorker`: `{ id, kind, status, taskId? }`.
Ghost variant while `compute.provisioning`, solid on `compute.ready`, plays a
shrink-and-fade collapse and is removed on `compute.released` — this is the literal
"if the scheduler kills 3, they collapse out of the scene" requirement. Because
fleets here can be numerically large (dozens of workers), this is the primary
instancing candidate: one drei `<Instances>` pool per `kind` (CPU/GPU/serverless each
get their own shared geometry+material), one `<Instance>` per live worker positioned
by a grid/pack layout selector, with per-instance color/emissive intensity encoding
status. LOD: beyond ~150 simultaneous instances, per-instance pulse animation is
dropped in favor of a single batched instanced-attribute color update per frame.

### NetworkLink
Renders the edges between NetworkNodes inside a world (Gateway-API, API-Auth,
API-DB, etc.) using drei's `<Line>`. Props: `{ id, worldId, fromMachineId,
toMachineId, kind }`, resolved from a static per-world-template topology definition.
A link only renders once **both** endpoint machines have a mounted NetworkNode
(i.e., both are READY) — same "don't invent state" rule applied to edges, not just
nodes. Disappears if either endpoint is released/destroyed. Not instanced
individually (few links per world); if link counts grow, batch into one merged
`<Line>` per world rather than per-edge components.

### AttackPath
Animates the attack physically propagating hop-by-hop (Auth→API→DB) as a small
traveling marker along a NetworkLink's curve. Props from the proposed
`AttackEvent`: `{ id, worldId, fromMachineId, toMachineId, techniqueId, status:
IN_PROGRESS|BLOCKED|SUCCEEDED, startedAt }`. Position is computed every frame as
`t = clamp((now - startedAt) / travelDuration, 0, 1)` along the parent link's curve
— deterministic and timestamp-derived (not physics/velocity state), which is what
lets `SpatialTimeline` scrub reconstruct the exact same position for a past instant.
Appears on the backend event that names that specific hop (an `agent.action` whose
payload references the technique/hop, or a dedicated attack-progression event once
Batch D defines one); resolves into a terminal decal (a static "scorched link"
marker) on reaching its destination or on `verification.failed`/`.passed`. LOD: cap
concurrent visible AttackPaths per world (e.g., 8); older ones collapse into the
scorched-link decal. All active travelers across a world share one small instanced
pool (cheap geometry — a spark/cone).

### AgentEntity
Represents one CALDERA (or GhostRange-native) red/blue agent operating on a
machine. Props: proposed `{ id, worldId, machineId, kind: RED|BLUE, status:
STARTED|ACTING|COMPLETED }`. Rendered as a small satellite marker (tetrahedron)
docked at its host NetworkNode, red/blue colored. Appears on `agent.started`,
flashes briefly on `agent.action` (subscribed narrowly by agent id so unrelated
agents don't re-render — see §4's per-entity selector pattern), removed on
`agent.completed`. Not instanced at M1's expected agent counts (few per world); note
for later — migrate to the same `<Instances>` pattern as ComputeNode if agent counts
grow materially.

### ExecutionTask
Renders one DAG node in the Execution space. Props from the proposed `Task`: `{ id,
dagId, kind, status: QUEUED|SCHEDULED|STARTED|COMPLETED|FAILED|SPECULATED,
dependsOn: string[], assignedComputeWorkerId? }`. Position comes from a topological
DAG-layout selector (x = depth, y/z = sibling spread) memoized per dag and only
recomputed when that dag's task-id set changes. `SPECULATED` gets a distinct
translucent/dashed-outline material to visually flag "this branch might get thrown
away" before it's known to have paid off. Appears on `task.queued`; advances
materially on `task.scheduled/started/completed/failed/speculated`; plays a collapse
and unmounts on terminal failure or speculative-prune (via the same deferred-removal
technique as WorldCollapse, §4). Instancing: DAGs can run into the hundreds of
tasks, so ExecutionTask uses the same `<Instances>`-per-`kind` fleet pattern as
ComputeNode, with dependency edges drawn as one batched `<Line>` set rather than
per-edge components; below a zoom/distance threshold, whole DAG subgraphs collapse
into a single aggregate "cluster" instance carrying a count badge.

### HypothesisBranch
Renders the fork connector in Multiverse space — the curved tube from a parent
World (or the originating Investigation) to a child World, visualizing "this World
represents remediation hypothesis X." This has no dedicated backend row; it's
derived purely from a World's `parentWorldId`/`investigationId`. Rendered as a
`<Line>` or thicker `<Tube>` between the two computed node positions. Unlike
NetworkNode, this can render **immediately** on `world.forked` even while the child
World is still `PROVISIONING` — the fork *decision* is real, known information
independent of whether infra has come up yet, so drawing it early does not violate
the "don't invent infra state" rule (only literal machine/compute state must wait).
Removed only if the parent World is destroyed. No instancing (branch count tracks
world count, always small).

### EvidenceArtifact
Renders one node in the Evidence constellation. Props from the proposed `Evidence`:
`{ id, kind: CLAIM|EXPLOIT|PATCH|REGRESSION, worldId?, relatedIds: string[],
summary, createdAt }`. Each kind gets a distinct simple glyph (tetrahedron=claim,
spike=exploit, shield=patch, warning-cube=regression), positioned by an
incrementally-updated force-directed layout (see §3 note below on avoiding a
physics engine) that nudges new nodes in via a lightweight spring lerp rather than
re-solving the whole graph. Appears on `evidence.created`; never removed within a
session (append-log semantics, consistent with Decisions.md's open evidence
provenance question), though superseded evidence can dim. Selecting one **never**
puts its text in 3D — it opens `DetailSurface` (§3, below). Given potentially large
counts over a long investigation, each kind gets its own `<Instances>` pool.

*Force layout note:* implement the incremental force pass with a small, dependency-light
solver (a handful of spring/repulsion terms ticked at low frequency, e.g. 10Hz, inside
a `useFrame` throttle, or `d3-force` run once per new-node-batch) — explicitly not a
physics engine, per the perf requirement to avoid unnecessary physics.

### ResourceFlow
Animated flow/ribbon visualizing a scheduler resource assignment — a task binding
to a compute worker, or (on the range side) data moving Gateway→API. Props: derived
from a `SchedulerDecision`'s `resultingWorkerIds`/`subjectTaskIds`, or from
`Task.assignedComputeWorkerId`. Reuses AttackPath's curve-interpolation technique
along a `<Line>` connecting ExecutionTask↔ComputeNode (or NetworkNode↔NetworkNode),
with a neutral "data" palette instead of AttackPath's threat palette. Appears when a
`scheduler.decision` assigns a task to a worker, or on `task.started` for an
already-assigned task; disappears on `task.completed`/`task.failed`/
`compute.released`. LOD: cap simultaneous visible flows (e.g., the 20 most recently
relevant); older assignments collapse to a static thin line with no particle
traffic.

### VerificationRing
A torus halo around a World or EvidenceArtifact indicating verification in
progress or its outcome. Props from the proposed `Verification`: `{ id,
targetWorldId | targetEvidenceId, status: STARTED|PASSED|FAILED }`. Spins while
`STARTED`; locks to a green/red pulse on `PASSED`/`FAILED` and fades out a fixed
delay after resolution — timed off the event timestamp so `SpatialTimeline` scrub
reproduces the same visual at a past instant. Appears on `verification.started`,
resolves on `verification.passed`/`verification.failed`. Instancing: all active
rings across the scene share one `<Instances>` ring pool (identical geometry, only
radius/color/spin-speed vary per instance).

### ThreatPulse
An ambient danger-signal field — an expanding shader-driven wavefront on a billboard
plane — distinct from AttackPath's discrete traveling marker; this is the "something
bad is active here" ambient glow. Props: **purely derived**, not event-sourced
directly — a selector computes `hasActiveAttack(machineId | worldId)` from currently
`IN_PROGRESS` AttackEvents. Implemented as a single custom `ShaderMaterial` with a
time uniform driving the expansion so cost is flat (GPU-driven) regardless of how
many pulses are visible; explicitly capped to at most one merged pulse per node
(never N overlapping pulses stacking on the same node) to bound draw calls. Has no
lifecycle event of its own — it appears/disappears as a pure function of derived
boolean state each render.

### WorldFork
The transient VFX that plays when a new World branches off: a spawn burst, the
HypothesisBranch line drawing in, RangeWorld materializing. Subscribes narrowly to
`world.forked` and keeps a short-lived (~2s TTL) local id list in a `ui`/transient
slice — explicitly *not* permanent domain state — to know which World/branch is
"newly arrived" and should animate its intro. Self-removes its transient flag after
the animation completes via a `useFrame`-driven local timer. No instancing (low,
bursty count).

### WorldCollapse
Mirror of WorldFork: plays an implode/fade/particle-scatter animation when a World
is pruned or fails terminally, driven by `world.destroyed`. Implements the
"deferred removal" pattern used across the doc (§4): on receipt of the destroy
event the store marks the entity `pendingRemoval: true` rather than deleting it
immediately, so WorldCollapse gets a fixed window (e.g., 900ms) to animate before a
`finalizeRemoval(id)` action actually deletes it from the normalized map. The same
pattern (and largely the same visual technique, parameterized by scale/silhouette)
is reused for ComputeNode and ExecutionTask removal.

### ProvisioningGhost
The shared "not real yet" presentational variant composed *by* NetworkNode and
ComputeNode (not independently mounted by its own event) whenever the backing
entity's status is `REQUESTED`/`PROVISIONING`: a translucent wireframe/dashed
outline with a loading-shimmer shader, deliberately distinct from the solid "ready"
material. This is the concrete, singular mechanism implementing "the UI must never
invent successful infra state ahead of reality" — there is exactly one place a
reviewer needs to check to confirm that rule holds. Props: `{ status, kind }` only
(picks silhouette). Reuses its parent's base geometry with a swapped material, so it
carries no LOD/instancing concerns of its own beyond its parent's.

### CostParticle
Small particles streaming from/around a World or ComputeNode to give an ambient
sense of burn rate. Props: derived, not event-sourced directly, from a
`costRatePerWorld`/`costRatePerWorker` selector — for M1, approximated as `(live
worker count) × (static hourly-rate lookup table per Vultr instance type)`, no live
billing API required. Rendered as one scene-wide instanced particle system with a
**hard cap** (e.g., 200 particles total, redistributed proportionally by cost
share across active worlds/workers) — this is the literal implementation of the
perf requirement's "capped particle counts": spawn rate is throttled so the cap is
never exceeded regardless of how many worlds/workers exist simultaneously. Scales
toward zero and stops spawning as a World's/worker's cost rate returns to zero on
release.

### SchedulerDecision
A short-lived annotation marking a moment the scheduler decided something (scale
up/down, assign, speculate, kill-speculative). Props from the proposed
`SchedulerDecision`: `{ id, decisionType, subjectTaskIds, resultingWorkerIds,
costEstimate, rationale, timestamp }`. Rendered as a `<Billboard>` chip (real 3D
sprite, not `<Html>`) near the affected ComputeNode/ExecutionTask cluster; clicking
it triggers a highlight pulse on the associated ResourceFlow(s) (the interaction
spec's "open scheduler decision → resource flow highlights"). The chip's icon/label
is 3D; the deeper rationale/log text opened on click goes through DetailSurface as
conventional 2D, same rule as EvidenceArtifact. Appears on `scheduler.decision`,
auto-fades after a few seconds unless pinned by selection. Not instanced
(event-rate-limited); capped visible history (e.g., last 30 live in-scene), older
ones reachable only via SpatialTimeline scrub.

### SpatialTimeline
The scrub control: a slim, mostly-2D HUD strip (a `<Html>`-anchored overlay with
tick marks, deliberately DOM-rendered for legible timestamps/labels, consistent with
keeping readable text out of 3D space) that sets `ui.timelineCursor` in the store on
scrub. It reads the store's append-only raw event log (kept specifically to make
scrubbing possible, see §5) to render tick density, and never mutates entities
directly — see §5 for the snapshot+replay mechanism that makes "historical world
state reconstructs" concrete. Not a rendered-geometry primitive; included here
because it owns real interaction/state logic that every other primitive's `useFrame`
timing (AttackPath's `t`, VerificationRing's fade) already implicitly depends on
(they compute against "now," where "now" is `timelineCursor ?? Date.now()`).

### WorldCamera
Owns the single `CameraControls` (drei) instance and all camera choreography:
default free-look, scripted "fly into a world," rail-style scroll progression, and
reset-to-overview. Reads `ui.selectedWorldId`/`ui.space` and a target's computed
bounding info (position + radius from a selector) — it never treats the camera's
Three.js transform as domain truth; "which world is selected" lives in Zustand,
only the ephemeral camera pose lives on the `CameraControls` object (see §4 hard-rule
note). Trigger: any change to `ui.selectedWorldId` (set by clicking a RangeWorld, by
SpatialTimeline navigation, or by the keyboard-accessible world list — see
`INTERACTION_MODEL.md`) drives the two-stage flight described in §6. No LOD; single
instance, one per `<Canvas>`.

### SelectionRaycaster
Thin coordinating logic, not really geometry, centralizing pointer→entity-id
resolution so click/hover semantics stay consistent across RangeWorld, NetworkNode,
ComputeNode, ExecutionTask, EvidenceArtifact, and SchedulerDecision. See §7 for the
concrete GPU-picking-vs-CPU-raycast decision; in short, each instanced fleet
attaches R3F's native pointer handlers directly to its `<Instances>` group and
resolves `event.instanceId` through a small shared `useInstanceIndex` helper plus a
`resolveSelection(space, kind, id)` utility that every `onClick` funnels through
into the store's `select*` actions. A global `onPointerMissed` on `<Canvas>` clears
selection. No instancing/LOD of its own (it's a hook + utility, not a mesh).

### DetailSurface
The conventional 2D panel that opens beside a selected node — logs, diffs,
rationale, evidence summaries. **Explicitly not a 3D component in the geometry
sense**: implemented as an ordinary React DOM panel (a sidebar, positioned overlay,
or drei `<Html>` anchor purely for screen-space docking convenience — the *content*
inside is standard HTML/CSS text, never a Three.js `<Text>` mesh). Props: whatever
`ui.selectedEvidenceId`/`selectedSchedulerDecisionId`/`selectedWorldId` resolves to
via a selector — the panel is a pure reader of store state, same as any 3D
primitive, it just renders to DOM instead of to the WebGL canvas. This is the direct
implementation of the evidence-space requirement that logs/diffs "must stay 2D,
never rendered floating in 3D."

---

## 4. State Architecture: one normalized entity store, sliced, with per-space selectors

**Decision: a single Zustand store, built from slice creators, holding normalized
entity maps for all three spaces plus one small `ui` slice — not three separate
per-space stores.**

### Why one store, not `multiverseStore` / `executionStore` / `evidenceStore`

The spaces are not actually independent domains — they're three views over one
event stream and a genuinely cross-referencing entity graph:

- A `World` (Multiverse) can have `Task`s speculatively running against it
  (Execution) and `Evidence` attached to it (Evidence space) — `SchedulerDecision`
  and `Verification` both reference across spaces.
- `SpatialTimeline` (required to "reconstruct historical world state" on scrub) has
  to replay the *entire* event log through one consistent set of reducers. If
  mutation logic were split across three stores, scrubbing would need to coordinate
  three independent snapshot/replay mechanisms and keep them in lockstep — a
  correctness hazard for no benefit.
- There is exactly one backend event transport (Redis/Valkey pub-sub per
  Decisions.md item 4) producing one ordered stream. One store means one dispatcher
  (`applyBackendEvent`) and one normalization codepath to test and reason about;
  three stores would mean deciding, for every event, which store(s) it touches, and
  keeping duplicate `Record<id, Entity>` bookkeeping utilities in sync across all
  three.

The counterargument for split stores is usually re-render isolation — but Zustand
already solves that within one store via per-slice selectors and `subscribeWithSelector`
+ shallow equality, so splitting stores buys no additional isolation here, only
duplicated plumbing. See "re-render isolation" below for how this is enforced
without three stores.

### Store shape

```ts
// packages/ui-3d/src/state/store.ts
import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

interface GhostRangeState {
  // ---- Multiverse entities ----
  incidents: Record<string, Incident>;
  investigations: Record<string, Investigation>;
  worlds: Record<string, WorldEntity>;              // + pendingRemoval?: boolean
  machines: Record<string, MachineEntity>;
  links: Record<string, NetworkLinkEntity>;
  attackEvents: Record<string, AttackEventEntity>;
  agents: Record<string, AgentEntity>;

  // ---- Execution entities ----
  tasks: Record<string, TaskEntity>;                // + pendingRemoval?: boolean
  computeWorkers: Record<string, ComputeWorkerEntity>;
  schedulerDecisions: Record<string, SchedulerDecisionEntity>;

  // ---- Evidence entities ----
  evidence: Record<string, EvidenceEntity>;
  verifications: Record<string, VerificationEntity>;

  // ---- Denormalized indices, maintained on every relevant mutation ----
  worldsByInvestigation: Record<string, string[]>;
  machinesByWorld: Record<string, string[]>;
  linksByWorld: Record<string, string[]>;
  attacksByWorld: Record<string, string[]>;
  tasksByDag: Record<string, string[]>;
  workersByKind: Record<'cpu' | 'gpu' | 'serverless', string[]>;
  evidenceByWorld: Record<string, string[]>;

  // ---- Raw event log (append-only; powers SpatialTimeline replay) ----
  eventLog: BackendEvent[];
  snapshots: { atSeq: number; state: EntitySlice }[]; // periodic, see §SpatialTimeline

  // ---- UI / transient (explicitly NOT domain truth) ----
  ui: {
    space: 'multiverse' | 'execution' | 'evidence';
    selectedWorldId: string | null;
    selectedTaskId: string | null;
    selectedEvidenceId: string | null;
    selectedSchedulerDecisionId: string | null;
    timelineCursor: number | null; // epoch ms; null = live
    recentlyForkedWorldIds: Set<string>; // WorldFork TTL set
  };

  // ---- One action per backend event, named 1:1 with the event for traceability ----
  applyBackendEvent(e: BackendEvent): void;
  finalizeRemoval(kind: 'world' | 'task' | 'computeWorker', id: string): void;

  // ---- UI actions ----
  selectWorld(id: string | null): void;
  selectTask(id: string | null): void;
  selectEvidence(id: string | null): void;
  setTimelineCursor(t: number | null): void;
}
```

Built with `create<GhostRangeState>()(subscribeWithSelector(immer((set, get) => ({ ...slices }))))`.
`immer` middleware makes the normalized-map mutations (`state.worlds[id].status = ...`)
ergonomic without hand-rolled spread chains; `subscribeWithSelector` is what lets
individual primitives subscribe to a narrow slice (see re-render isolation below).

Slices are still authored as separate files (`createMultiverseSlice`,
`createExecutionSlice`, `createEvidenceSlice`, `createUiSlice`) combined with
Zustand's documented slice pattern — organizationally separate, runtime-unified.
This gets the maintainability benefit people usually want from "separate stores"
without the coordination cost.

### Per-space selectors

`packages/ui-3d/src/state/selectors/{multiverse,execution,evidence}.ts` export pure
functions like `selectWorldsForInvestigation(state, investigationId)`,
`selectTasksForDag(state, dagId)`, `selectActiveAttacksForMachine(state, machineId)`.
Components use them via `useGhostRangeStore(selector, shallow)` (Zustand's `shallow`
from `zustand/shallow`) so an unrelated entity mutation doesn't re-render a component
whose derived array is referentially different but value-equal. For anything hotter
than that (e.g., ExecutionTask's per-dag layout, EvidenceArtifact's force layout),
memoize the derived positions keyed by the *id set* of the relevant slice (a cheap
join of sorted ids), not by the whole state, so a status-only change doesn't
retrigger a layout recompute.

### Enforcing the hard rule (business state never in Three.js objects)

Every primitive in §3 receives entity data as **props**, computed by a container
component in the relevant space's Scene (e.g., `apps/web/src/scenes/MultiverseScene.tsx`)
via the selectors above — primitives themselves never call `useGhostRangeStore`
directly for domain fields, only (optionally) for `ui.*` selection state needed to
render a "selected" outline. The only state allowed to live on a `ref`/Three.js
object is non-domain animation state: current tween `t`, a shader time uniform, a
particle's current interpolated position — anything that, if lost on remount, would
only cost a visual restart, never a wrong answer about what actually happened in the
backend. `WorldCollapse`'s `pendingRemoval` flag is domain-adjacent but still lives
in the store (not in Three.js), which is exactly why deferred removal is a store
concept (§3) and not a component-local one.

---

## 5. Backend event → store mutation mapping

`applyBackendEvent` is one exhaustive switch, each case a small, individually
testable pure-ish mutator (pure in the sense of "same event + same prior state →
same next state," which is also what makes `SpatialTimeline` replay work):

| Event | Mutation |
|---|---|
| `world.requested` | Insert `worlds[id]` with `status: REQUESTED`; push id into `worldsByInvestigation[investigationId]`. |
| `world.provisioning` | `worlds[id].status = PROVISIONING`. |
| `world.ready` | `worlds[id].status = READY`. |
| `world.forked` | Insert child `worlds[childId]` (`status: REQUESTED`, `parentWorldId`); add `childId` to `ui.recentlyForkedWorldIds` (TTL-cleared by a `setTimeout` dispatching a `clearRecentFork` UI action ~2s later — WorldFork reads this set). |
| `world.destroyed` | `worlds[id].status = DESTROYED \| FAILED \| PRUNED` (payload-specified) and `worlds[id].pendingRemoval = true`; WorldCollapse's timer later calls `finalizeRemoval('world', id)`, which deletes the entry and prunes it from `worldsByInvestigation`. |
| `task.queued` | Insert `tasks[id]` (`status: QUEUED`); push into `tasksByDag[dagId]`. |
| `task.scheduled` | `tasks[id].status = SCHEDULED`; set `assignedComputeWorkerId`. |
| `task.started` | `tasks[id].status = STARTED`. |
| `task.completed` | `tasks[id].status = COMPLETED`. |
| `task.failed` | `tasks[id].status = FAILED`, `pendingRemoval = true` (post-animation `finalizeRemoval('task', id)`). |
| `task.speculated` | Insert or mark `tasks[id].status = SPECULATED` (a speculative branch task may arrive as a fresh queued+speculated pair, or an existing task may be flagged; both are represented as the same status enum value so ExecutionTask needs no special-case prop). |
| `agent.started` | Insert `agents[id]` (`status: STARTED`). |
| `agent.action` | Update `agents[id].lastActionAt`/payload (used only for the AgentEntity flash — not persisted beyond latest). |
| `agent.completed` | `agents[id].status = COMPLETED`; component-level cleanup unmounts it (agents are removed immediately, no collapse animation is specced for them at M1). |
| `evidence.created` | Insert `evidence[id]`; push into `evidenceByWorld[worldId]` if present. |
| `verification.started` | Insert `verifications[id]` (`status: STARTED`, `targetWorldId`/`targetEvidenceId`). |
| `verification.passed` / `verification.failed` | `verifications[id].status = PASSED \| FAILED`; VerificationRing's own fade timer removes the ring visually without deleting the record (verification history is kept, same append-log philosophy as evidence). |
| `compute.requested` | Insert `machines[id]` or `computeWorkers[id]` (payload disambiguates range-topology vs scheduler-fleet) with `status: REQUESTED`. |
| `compute.provisioning` | `...status = PROVISIONING`. |
| `compute.ready` | `...status = READY` — this is the sole trigger that flips NetworkNode/ComputeNode from `ProvisioningGhost` to solid. |
| `compute.released` | `...status = RELEASED`, `pendingRemoval = true` → deferred `finalizeRemoval`. |
| `scheduler.decision` | Insert `schedulerDecisions[id]`; this is also the trigger ResourceFlow subscribes to for drawing task↔worker assignment flows. |

Every case also appends the raw event to `eventLog` (bounded — see §SpatialTimeline
snapshotting below) *before* mutating, so replay-for-scrub can always reconstruct
prior states by re-running this exact table against an older log slice.

**SpatialTimeline snapshot/replay, concretely:** every 200 events (or on every
`world.*` transition, whichever is more frequent), push `{ atSeq, state:
structuredClone(entitySlices) }` into `snapshots` (drop old snapshots beyond a cap,
e.g., last 20, since M1 doesn't need unbounded history scrub — only "recent
investigation" depth). On `setTimelineCursor(t)`, find the latest snapshot at or
before `t`, then replay `eventLog` entries between that snapshot and `t` through the
*same* mutator functions into a scratch copy, producing a read-only historical
projection that a `useHistoricalOrLive()` wrapper hands to selectors in place of live
state whenever `ui.timelineCursor !== null`. This guarantees exactly one
normalization codepath serves both live and historical rendering.

---

## 6. WorldCamera: "fly into a world" transition

**Recommendation: drei's `<CameraControls>`** (wrapping `camera-controls` by
yomotsu), not a hand-rolled `react-spring`/`framer-motion-3d` tween, and not
`OrbitControls` plus manual lerp.

Why: `CameraControls` already gives (a) a promise-returning `setLookAt(px, py, pz,
tx, ty, tz, enableTransition)` for scripted cinematic moves, (b) `fitToSphere`/
`fitToBox` to frame an arbitrary world's bounding volume without hand-computing
distances, (c) interruptible/cancelable transitions (so clicking a different world
mid-flight doesn't fight the previous tween), and (d) the *same* object still
drives ordinary mouse/touch/keyboard orbit-and-zoom for free browsing — one
component serving both the scripted-flight and the free-look/accessible-fallback
needs, instead of maintaining two camera systems. Rolling this by hand with
react-spring would mean re-implementing damping, interruption, and framing math that
`CameraControls` already has, purely to avoid one dependency drei already selects
for us.

**Concrete flight, for "click World B in Multiverse → reveal its topology":**

1. On `ui.selectedWorldId` change (Multiverse → a world), `WorldCamera` computes the
   target world's bounding sphere (position + radius from a selector over its
   machines' layout, falling back to a fixed default radius if machines haven't
   materialized yet) and calls `controls.fitToSphere(targetSphere, true)` — stage 1,
   framing the whole world from outside.
2. On that promise resolving, the space-level container swaps rendered content: the
   Multiverse graph's other RangeWorld/HypothesisBranch nodes fade/unmount (or are
   simply occluded — implementation detail left to Agent 17), and that world's
   NetworkNode/NetworkLink/AttackPath topology mounts.
3. `WorldCamera` immediately issues a second `setLookAt(...)` to the topology's
   canonical overview pose (a fixed offset computed from the topology's own bounding
   box) — stage 2, settling into the "inside the world" vantage.
4. Backing out (Escape, or a breadcrumb click — see `INTERACTION_MODEL.md`) reverses
   the two stages and clears `ui.selectedWorldId`.

**Scroll/wheel "camera progression"** (Multiverse ambient browsing, not the
click-to-fly-in above) is handled by the *same* `CameraControls` instance: wheel
deltas are intercepted and translated into `controls.dolly(delta, true)` /
`controls.truck(...)` calls constrained to a per-space min/max range (set via
`controls.minDistance`/`maxDistance` and, where relevant, `minPolarAngle`/
`maxPolarAngle`), rather than free 6-DOF flight — this gives the "progression along
the investigation" feel the interaction model wants without a bespoke spline-camera
system. See `INTERACTION_MODEL.md` §2 for the full event table.

---

## 7. GPU picking / raycasting for SelectionRaycaster

**Recommendation: ordinary CPU-side raycasting via R3F's built-in pointer events on
`InstancedMesh`, not a color-ID GPU-picking render pass.**

R3F's raycaster already special-cases `InstancedMesh`: a pointer event on an
instanced object's `onClick`/`onPointerOver` includes `event.instanceId`, resolved
via Three.js's own `Raycaster.intersectObject` support for instanced geometry — no
extra render target, no encoding entity ids into a hidden color buffer, no second
render pass. This is the right call at M1 scale specifically because every
instancing candidate in §3 (ComputeNode, ExecutionTask, EvidenceArtifact,
VerificationRing, CostParticle) is capped in the low hundreds of instances at most
(the perf requirement enforces this anyway) — CPU raycasting against that many
bounding volumes is well under a millisecond, nowhere near the regime (tens of
thousands+ of pickable objects) where GPU color-ID picking earns back its added
complexity. Revisit only if a later milestone removes the instance caps.

Concrete mechanism:
- Each fleet component (`ComputeNode`'s `<Instances>` block, etc.) maintains its own
  `index → entityId` array via a small shared hook, `useInstanceIndex(ids: string[])`,
  kept in sync with render order (the array *is* `ids`, so this is nearly free — the
  hook mainly exists to give one canonical name/pattern for it).
- A single shared `resolveSelection(space, kind, id)` utility (living next to
  `SelectionRaycaster`) is what every primitive's `onClick` calls — it just forwards
  to the matching store `select*` action. This is the "one canonical place a pointer
  event becomes a domain selection," satisfying the requirement without a heavyweight
  custom raycasting subsystem.
- Non-instanced primitives (RangeWorld, HypothesisBranch, SchedulerDecision chips)
  attach `onClick` directly to their own mesh/group — no `instanceId` involved, just
  the entity id captured in the closure.
- `<Canvas onPointerMissed={() => resolveSelection(null)}>` clears selection when a
  click hits nothing, which is the mechanism behind "click empty space to deselect."
- To keep raycasting itself cheap regardless, prefer simple bounding-proxy geometry
  for `raycast` where a primitive's visual mesh is more detailed than its hit target
  needs to be (Three.js's `Mesh.raycast` already tests the bounding sphere first;
  no extra library like `three-mesh-bvh` is needed at these counts — adding it would
  be exactly the kind of complexity the perf requirement asks us to avoid until
  proven necessary).

---

## 8. Performance checklist (traceability back to the stated requirement)

| Requirement | Where it's satisfied |
|---|---|
| Instancing for repeated geometry | ComputeNode, ExecutionTask, EvidenceArtifact, VerificationRing, AttackPath travelers, CostParticle — all `<Instances>`-based (§3). |
| No downloaded assets/large textures | Every primitive is procedural BufferGeometry + ShaderMaterial/MeshStandardMaterial; no GLTF/texture imports anywhere in this doc. |
| No unnecessary physics engine | EvidenceArtifact's layout uses a lightweight manual/`d3-force` spring pass, explicitly not a physics engine (§3 note). |
| LOD for large worlds | drei `<Detailed>` on NetworkNode; DAG-cluster collapse on ExecutionTask; both in §3. |
| Capped particle counts | CostParticle hard-capped at ~200 total (§3); AttackPath capped concurrent-per-world (§3). |
| Adaptive pixel ratio | `<Canvas dpr={[1, 2]}>` plus drei `<PerformanceMonitor>` stepping dpr/effect quality down under sustained frame-time pressure — implemented once, centrally, in the root `<Canvas>` setup, not per-primitive. |
| Suspend animation when off-screen | `frameloop="demand"` as the `<Canvas>` default (invalidated on store mutation and camera interaction via R3F's `invalidate()`), switching to `"always"` only while an active tween/particle/attack animation is in flight — tracked by a small `activeAnimationCount` counter incremented/decremented by any primitive with a running `useFrame` tween. |
| Minimize React re-render propagation | Single-store-with-selectors + `shallow` equality (§4); primitives take props, not direct store subscriptions, so a container's selector is the only re-render boundary. |
| Profile frame time | `<PerformanceMonitor>` (drei) wired to the adaptive-dpr logic above doubles as the profiling hook; recommend also wiring its `onIncline`/`onDecline` callbacks to a dev-only on-screen frame-time readout during Agent 17-19's build-out. |
