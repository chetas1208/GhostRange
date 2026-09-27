# Final UI specification (M20 convergence)

Preserves M1–M3 spatial command-center — **not** a dashboard redesign.

## Shell

- One `GhostCanvas` (R3F), three scene groups: Multiverse / Execution / Evidence (visibility by `mode`).
- DOM: thin top HUD, bottom timeline, contextual right inspector (340–420px), transient CommandSurface (⌘K).
- **No** fourth tab, **no** permanent left sidebar, **no** permanent subsystem panels.

## HUD

| Zone | Content |
|------|---------|
| Left | GHOSTRANGE + campaign label |
| Center | MULTIVERSE · EXECUTION · EVIDENCE pills |
| Right | ● LIVE / ◇ SIMULATED / ◷ HISTORY · $cost · N WORKERS |

## Modes map M1–M20

| Mode | Subsystems surfaced spatially |
|------|-------------------------------|
| Multiverse | Twin, topology, forks, attack/causal paths, remediation worlds, production shadow |
| Execution | DAG, workers, scheduler decisions, ActionGate/Permit, recovery |
| Evidence | Claims, artifacts, verification ring, Arena sealed summary, evolve markers |

## Operator integrations

GhostGate, GhostWatch, Mesh, Causal **only** inside CommandSurface → OperatorIntegrations (evidence-gated panels).

## Live honesty

Workers render only from store worker records. LIVE/SIM/HISTORY always visible. No fixture posing as live when `VITE_DATA_SOURCE=live`.

## M20 campaign

`CommandSurface` → Start M20 golden campaign → `POST /v1/campaigns/golden`. Optional `VITE_BOOTSTRAP_M20=true` with live data source.

See also: `THREE_D_ARCHITECTURE.md`, `INTERACTION_MODEL_FINAL.md`, `EVENT_TO_VISUAL_MAPPING.md`.
