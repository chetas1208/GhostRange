# Accessibility (M20)

- `prefers-reduced-motion`: global scale via `--gr-motion-scale` and `useReducedMotionGlobally`.
- Keyboard: mode shortcuts, Escape clear/focus out, Tab to HUD/command controls.
- `SelectionAnnouncer` live region for selection changes.
- Inspector provides DOM text for all selected entities (workers, tasks, worlds, claims).
- Color not sole signal: shape/motion/labels differentiate task states and connection status.
- 3D-heavy actions have DOM equivalents in inspector or command surface where feasible.

Mobile: not primary; layout degrades to overlay inspector at narrow widths.
