# M20 UI convergence

## UI agents (30) — summary

| ID | Role | Status |
|----|------|--------|
| UI-01 | Visual audit | done |
| UI-02 | Design tokens | done (`tokens.css`, `VISUAL_LANGUAGE.md`) |
| UI-03 | Environment | done (DepthFog, grid, lighting) |
| UI-04–UI-10 | Multiverse/causal/remediation | partial (existing ui-3d) |
| UI-11–UI-17 | Execution/shield/runtime | partial |
| UI-18–UI-20 | Evidence/Arena/Evolve | partial (SealedRange in EvidenceScene) |
| UI-21–UI-23 | Timeline/inspector/HUD | done (shell cleanup) |
| UI-24 | Accessibility | partial (doc + announcer) |
| UI-25 | Performance | partial (selector audit, BloomGate) |
| UI-26 | Selector audit | done (primitive selectors) |
| UI-27–UI-28 | Screenshot/E2E | in_progress (`make ui-acceptance`) |
| UI-29–UI-30 | Review | **UI-NO-GO** (pending green acceptance) |

## Changes (this pass)

- Removed duplicate **ModeDock** (left vertical nav) and **DirectorSchedulerStrip** / **ExecutionDecisionsPanel** from default shell.
- Moved M11–M14 operator panels to **CommandSurface** only.
- HUD: LIVE/SIM/HISTORY symbology, campaign context line, restrained mode pills.
- **DepthFog**, selective bloom selectors fixed (React #185 prevention).
- M20 campaign start from CommandSurface; live bootstrap via `campaignStream` (snapshot→SSE).
- M20 acceptance: Playwright E2E/visual, semantic capture script, `make ui-acceptance`.
- Live timeline scrub via `liveEventBuffer` (no fixture).
- Coordination: `docs/milestones/M20_UI_ACCEPTANCE_COORDINATION.md`.
- Documentation set under `docs/ui/FINAL_*`.

## UI-30 decision: **UI-NO-GO**

Backlog closed in repo: `m20_ui_events`, E2E (golden/SSE/keyboard/visual), semantic 24-frame capture, perf + fixture audit, docker acceptance path.

Remaining for **UI-GO**: green `bash scripts/m20-ui-acceptance-docker.sh`, 24 reviewed frames, UI-28/29/30 sign-off.
