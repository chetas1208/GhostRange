# Final screenshot acceptance (M20)

**Visual design:** locked — do not redesign for acceptance.

**Capture path:** `artifacts/screenshots/ui-final/`  
**Automation:** `node scripts/capture-m20-ui.mjs` (after production preview + live API)  
**Index:** `artifacts/screenshots/ui-final/index.html`  
**One-shot:** `make ui-acceptance`

| # | File | Semantic trigger | LIVE/SIM |
|---|------|------------------|----------|
| 01 | 01-empty.png | initial shell before campaign | LIVE/OFFLINE |
| 02 | 02-production-world.png | `hasActiveWorld` or seq≥8 | LIVE |
| 06 | 06-execution-dag.png | mode=execution, seq≥14 | LIVE |
| 07 | 07-worker-provisioning.png | `workerProvisioning` | LIVE |
| 20 | 20-verification.png | `verificationRing===passed` or campaign COMPLETED | LIVE |
| 22 | 22-history.png | timeline scrub → `connection===REPLAY` | HISTORY |
| 23 | 23-final-teardown.png | `workerCount===0` | LIVE |
| 24 | 24-final-golden-path.png | post-complete evidence mode | LIVE |

**Rules:** no fixture timeline for LIVE acceptance builds (`VITE_DATA_SOURCE=live`).  
**Baselines:** update only via `npm run screenshots:m20:update` after intentional visual change.  
**UI-30:** **UI-NO-GO** until UI-28/29/30 human review (24/24 + manifest + Docker E2E/visual currently green).
