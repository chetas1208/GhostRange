# Camera system (final)

- Default multiverse: elevated `[0, 6, 12]`, FOV 45 — production world centered, negative space preserved.
- `CameraRig` transitions on `mode` and `focusedWorldId` with reduced-motion shortening.
- `OrbitControls`: pan disabled, polar capped — guided instrument, not free flight.
- States: OVERVIEW (multiverse), WORLD_FOCUS, EXECUTION_OVERVIEW (mode=execution), EVIDENCE_OVERVIEW (Z offset -15 group).

Dolly: `cameraDolly` integer adjusted via DepthControls DOM only.
