# GhostRange Interaction Model (M1)

Author: Agent 16 (3D Systems Architect). Companion to `THREE_D_ARCHITECTURE.md`,
which this doc assumes (component names, store shape, `WorldCamera`/`CameraControls`
choice, `SelectionRaycaster` mechanism). Written so Agents 17/18/19 can wire event
handlers directly against the tables below.

Hard requirement carried over from the brief: **every gesture-driven interaction
below must have a conventional, non-gesture equivalent** — keyboard and/or discrete
click, reachable without a trackpad/wheel/drag. Gesture-only navigation is
explicitly disallowed. §3 is the accessible-fallback spec, not an afterthought.

---

## 1. Interaction principle

All interactions are **selection-driven**, not direct-manipulation-driven: a
gesture (click, wheel, drag) or its keyboard equivalent updates `ui.*` state in the
store (`selectedWorldId`, `selectedTaskId`, `timelineCursor`, etc. — see
`THREE_D_ARCHITECTURE.md` §4); `WorldCamera` and the relevant scene components react
to that state change. Nothing in the 3D layer has a private notion of "what's
selected" that the DOM/keyboard layer can't also set. This is what makes every row
in §2 have a straightforward accessible-fallback row in §3: the fallback just sets
the same store field through a different input path.

---

## 2. Event → camera/scene response table

| # | Trigger (gesture) | Space | Handler | Store mutation | Camera response | Scene response |
|---|---|---|---|---|---|---|
| 1 | Scroll/wheel | Multiverse (ambient) | `WorldCamera`'s wheel listener on `<Canvas>` | none (camera-only; no domain state changes) | `controls.dolly(delta, true)` / `truck(...)` constrained to the space's min/max range — reads as "progressing" through the investigation depth, not free flight | none — this is pure camera movement, not a selection |
| 2 | Click a `RangeWorld` node | Multiverse | `RangeWorld`'s `onClick` → `resolveSelection('multiverse','world', id)` | `ui.selectedWorldId = id` | `WorldCamera` runs the two-stage fly-in from `THREE_D_ARCHITECTURE.md` §6 (`fitToSphere` → topology overview `setLookAt`) | Multiverse graph occludes/fades; that World's NetworkNode/NetworkLink/AttackPath topology mounts |
| 3 | Click an `AttackPath` traveler or its parent `NetworkLink` | Topology (inside a World) | `AttackPath`'s `onClick` → `resolveSelection('multiverse','attack', id)` | `ui.selectedAttackId = id` | none (camera holds) | Topology "isolates/highlights": non-participating NetworkNode/NetworkLink dim (opacity step-down via a `isDimmed` prop derived from `selectedAttackId`); the selected path's full hop chain (already-completed + current + predicted-next hop if known) is emphasized; `DetailSurface` opens with the attack's technique id / timestamps / affected machines as 2D text |
| 4 | Click a `SchedulerDecision` chip | Execution | chip's `onClick` → `resolveSelection('execution','decision', id)` | `ui.selectedSchedulerDecisionId = id` (pins the chip open, cancels its auto-fade) | none | The associated `ResourceFlow`(s) (`resultingWorkerIds`/`subjectTaskIds`) get a highlight pulse; `DetailSurface` opens with `rationale`/`costEstimate` as 2D text |
| 5 | Click an `EvidenceArtifact` node | Evidence | node's `onClick` → `resolveSelection('evidence','artifact', id)` | `ui.selectedEvidenceId = id` | small `fitToSphere`-style nudge to keep the node in frame (not a full fly-in — evidence space stays in one continuous view) | Constellation "rearranges": the force-layout selector reruns with the selected node's `relatedIds` weighted to pull those neighbors closer / push unrelated nodes outward (still the lightweight spring pass from `THREE_D_ARCHITECTURE.md` §3, not a full re-layout); `DetailSurface` opens beside it with logs/diff/summary as conventional 2D text — **never** rendered as floating 3D text |
| 6 | Drag the `SpatialTimeline` scrub handle | Any (global HUD) | `SpatialTimeline`'s DOM drag handler | `ui.timelineCursor = t` | camera pose itself does not change on scrub — only entity visual state does | Every primitive re-reads its props from the historical projection (`useHistoricalOrLive()`, see `THREE_D_ARCHITECTURE.md` §5) instead of live state: worlds/machines/tasks/evidence render exactly as they existed at `t`, including entities already removed live (rendered from the snapshot+replay projection, not the live normalized maps) |
| 7 | Click empty space / background | Any | `<Canvas onPointerMissed>` | clears the relevant `ui.selected*Id` for the current space | none, or camera eases back to the space's default overview pose if a fly-in was active | Dimming/highlighting/rearranging from rows 3-5 reverts |
| 8 | Click a breadcrumb ("Investigation > World B > Auth machine") | Any | breadcrumb DOM `onClick` | sets `ui.selectedWorldId`/clears deeper selections as appropriate | reverse of row 2's fly-in (back out one stage) | Topology unmounts, Multiverse graph re-appears |

Rows 2-5's "camera response: none" (rows 3-4) is intentional — selection-driven
highlighting should not also move the camera unless framing genuinely requires it
(row 5's small nudge), so that clicking through several evidence nodes in sequence
doesn't feel like a slideshow of camera jumps.

---

## 3. Accessible / non-gesture fallback (mandatory, not optional)

Every row in §2 has a keyboard/discrete-click path that sets the exact same store
field. None of this is a separate "accessibility mode" toggle — it's always present,
laid out as a conventional 2D control surface alongside the 3D canvas (a sidebar +
breadcrumb + timeline scrubber that are DOM elements regardless of input method).

| Gesture row (§2) | Keyboard / discrete-click equivalent |
|---|---|
| 1. Scroll/wheel camera progression | A visible "Depth" slider or `PageUp`/`PageDown` (and `+`/`-`) step the same dolly distance in fixed increments when the canvas or its container has focus. Also reachable via explicit "Zoom in/out" buttons in the HUD, not just keys, for pointer-only users who can't scroll. |
| 2. Click a World node | The sidebar renders an always-present, focusable, screen-reader-labeled list of current Worlds (mirrors what's visible in-scene, sourced from the exact same selector as the 3D layer). `Tab` reaches a World list item; `Enter`/`Space` fires the identical `selectWorld(id)` action as a click, triggering the same fly-in. `Escape` (or a visible "Back to Multiverse" button) reverses it. |
| 3. Select an AttackPath | The DetailSurface sidebar, when a World is open, lists active/recent attack hops as a focusable list (`role="list"`, one `role="listitem"` per hop with technique id + status text). `Enter` on an item sets `selectedAttackId` exactly as a click would. |
| 4. Open a SchedulerDecision | Execution space's HUD keeps a chronological, focusable "Decisions" list (not only the fading 3D chips) — same data, same `select*` action on `Enter`. This also solves the "chip already auto-faded" problem: the list persists past the chip's visual fade. |
| 5. Select Evidence | Evidence space's sidebar is a conventional filterable/searchable list of all EvidenceArtifacts (kind, summary, timestamp) — this is also just good UX for logs/diffs, not accessibility theater. `Enter`/click sets `selectedEvidenceId` identically to clicking the 3D node. |
| 6. Timeline scrub (drag) | The `SpatialTimeline` HTML `<input type="range">` (a real range input, not a custom drag-only widget) is natively keyboard-operable: arrow keys step it, `Home`/`End` jump to start/live. Screen readers announce its value via standard range-input semantics. |
| 7. Click empty space to deselect | A visible "Clear selection" control per space, plus `Escape` globally. |
| 8. Breadcrumb navigation | Breadcrumbs are ordinary `<nav><a>`/`<button>` elements — keyboard-focusable and screen-reader-navigable by construction; nothing special needed beyond not reinventing them as 3D objects. |

Additional cross-cutting fallbacks:
- **Camera orbit/pan without a mouse:** `CameraControls` (drei) supports keyboard
  binding out of the box (arrow keys for truck/rotate, configurable); wire this
  explicitly rather than relying on default browser focus behavior, and document the
  bindings in an on-screen "?" key hint overlay.
- **Reduced motion:** honor `prefers-reduced-motion` (and a manual in-app toggle) by
  short-circuiting `WorldCamera`'s scripted flights to instant cuts (`setLookAt(...,
  false)`, no transition) and disabling ambient animations that aren't
  information-bearing (ThreatPulse's expansion, CostParticle drift) while keeping
  status-bearing state changes (color/material swaps) intact — motion is decoration
  here, not the only channel for information, which is precisely why every 3D
  status cue (§3 of `THREE_D_ARCHITECTURE.md`) is designed as color/shape/material
  rather than motion-only.
- **No pure hover-only affordances:** anything that highlights on `onPointerOver` in
  the 3D scene (row 3/5's hover previews, if added later) must also be reachable via
  focus (`:focus-visible`-equivalent state driven by the same keyboard list items in
  the table above) — hover is a convenience layer on top of the click/`Enter`
  behavior, never a parallel feature only pointer users get.
- **Non-3D full app usability:** because every 3D primitive is a pure function of
  store state that a DOM sidebar can equally read and every 3D-only interaction has
  a listed DOM equivalent above, a user could in principle drive the entire
  investigation (browse worlds, inspect attacks, review scheduler decisions, read
  evidence, scrub history) with the `<Canvas>` never receiving focus at all. That's
  the concrete bar this doc holds itself to for "not pure gesture-only nav."
