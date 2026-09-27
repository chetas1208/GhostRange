# Multiverse 3D (tactical)

## Question answered

**What worlds exist, how are they related, and what is happening inside them?**

## Scene ownership

- `MultiverseScene.tsx` — world clusters, forks, workers, attacks.
- `MultiverseOrbitField.tsx` — optional slow orbit of child worlds (disabled when `prefers-reduced-motion`).
- Layout: `selectWorldLayout()` — polar orbit around source anchor.

## Lineage

- `forks[]` → `HypothesisBranch` edges parent → child.
- Progress along branch = **discrete lifecycle** (`REQUESTED` / shell / `network_ready`), not arbitrary percentage.

## Interaction

- OrbitControls on canvas (user rotates world).
- Select world → `InspectorShell` / `WorldInspector`.
- Camera levels: wheel without shift; shift+wheel scrubs timeline.

## Data

Worlds only from events — no `/v1/worlds` REST yet. See `TACTICAL_UI_AUDIT.md`.
