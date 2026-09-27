# GhostRange UI Specification

**Document type:** Source-of-truth UI and interaction specification  
**Project:** GhostRange — The Cyber Multiverse  
**Status:** Locked design direction  
**Primary modes:** Multiverse · Execution · Evidence  
**Primary UI rule:** Operational visuals are 3D and independently coded; readable text stays DOM.

This file indexes implementation in the monorepo. The complete §1–44 specification (philosophy, components, acceptance, screenshots) is the product lock document; agents should treat **§21 (event mapping)** and **§42 (component inventory)** as merge gates together with [`LIVE_STATE_MAPPING.md`](./LIVE_STATE_MAPPING.md).

---

## Implementation map (§3–4, §42)

| Area | Location |
|------|----------|
| AppShell, one canvas | [`apps/web/src/app/AppShell.tsx`](../../apps/web/src/app/AppShell.tsx) |
| GhostCanvas, camera, interaction | [`apps/web/src/ui/canvas/`](../../apps/web/src/ui/canvas/) |
| Multiverse / Execution / Evidence scenes | [`apps/web/src/ui/scenes/`](../../apps/web/src/ui/scenes/) |
| 3D primitives (§42 inventory) | [`packages/ui-3d/src/`](../../packages/ui-3d/src/index.ts) |
| DOM HUD (§4, §28) | [`apps/web/src/components/dom/hud/`](../../apps/web/src/components/dom/hud/) |
| Inspector (§9–11, §15) | [`apps/web/src/components/dom/inspector/`](../../apps/web/src/components/dom/inspector/) |
| Command surface (§14) | [`apps/web/src/components/dom/command/CommandSurface.tsx`](../../apps/web/src/components/dom/command/CommandSurface.tsx) |
| State & §21 mapping | [`apps/web/src/state/eventReducer.ts`](../../apps/web/src/state/eventReducer.ts) |
| Tokens & motion (§18) | [`apps/web/src/styles/tokens.css`](../../apps/web/src/styles/tokens.css) |
| Screenshot capture (§38) | [`scripts/capture-ui-snapshots.mjs`](../../scripts/capture-ui-snapshots.mjs) → `artifacts/screenshots/m2/` |

---

## Non‑negotiables (§43)

1. One primary WebGL canvas; three modes toggle scene groups — not separate full-screen apps.
2. Backend events drive lifecycle visuals in LIVE mode; FIXTURE is explicitly labeled.
3. No solid compute or interactive world topology before `compute.ready` / `world.ready`.
4. No primary tabs beyond the three modes; inspector sub-sections (Overview / Compute / Evidence) are contextual only.
5. No permanent left navigation sidebar (§5.2); accessibility lists live in inspector / mode context panels (§36).

---

## Related docs

- [THREE_D_ARCHITECTURE.md](./THREE_D_ARCHITECTURE.md)
- [INTERACTION_MODEL.md](./INTERACTION_MODEL.md)
- [LIVE_STATE_MAPPING.md](./LIVE_STATE_MAPPING.md)
- [EVENTS_CONTRACT.md](./EVENTS_CONTRACT.md)

---

## §38 Screenshot acceptance (12 states)

Captured via Playwright against preview/dev:

1. `multiverse-empty.png`
2. `multiverse-provisioning.png`
3. `multiverse-ready.png`
4. `multiverse-attack-active.png`
5. `multiverse-world-fork.png` (M1 fixture or fork events)
6. `execution-dag.png`
7. `execution-provisioning-worker.png`
8. `execution-speculative-split.png`
9. `evidence-unverified-claim.png`
10. `evidence-verified-claim.png`
11. `teardown-in-progress.png`
12. `world-destroyed-history.png`

Run: `npm run screenshots:docker` (build + preview + Playwright in Docker), or `npm run build && npm run preview` then `node scripts/capture-ui-snapshots.mjs` when host Chromium is available.

**M2 fixture:** default `VITE_FIXTURE=m2` (`m2-auth-lab-v1.jsonl`) includes fork branches for frame 05. Use `npm run screenshots:fork` for the M1 multiverse fork timeline only.
