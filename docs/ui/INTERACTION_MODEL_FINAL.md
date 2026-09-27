# Interaction model (final)

Based on `INTERACTION_MODEL.md` with M20 locks:

- **Primary modes:** keys `1` `2` `3` or center pills.
- **Selection:** click 3D object → inspector; background click / Escape clears.
- **Focus:** double-click world → `focusWorld`; Escape steps camera out via `popCameraLevel`.
- **Command surface:** ⌘K / Ctrl+K — campaign start, operator integrations (not navigation).
- **Timeline:** bottom scrub reconstructs state (`replayTimeMs`); HUD shows ◷ HISTORY when scrubbing.
- **Depth:** small +/- control bottom-right (not scroll-hijack).
- **No** permanent left mode dock (removed M20).

Camera levels: `multiverse` → `world` → `execution` (see `CameraRig`).
