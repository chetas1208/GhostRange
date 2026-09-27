# Cost visualization

## HUD (`CostIndicator`)

| Mode | Display |
|------|---------|
| LIVE | `ACCRUED EST.` + backend `display.known_total` |
| LIVE partial | `· PARTIAL` when `unknown_components` non-empty |
| LIVE error | `COST UNKNOWN` |
| Fixture | `SIM EST.` + fixture accumulator (not provider truth) |

Never show unqualified `$0.42`.

## Inspectors (target)

- **Campaign:** categories, known total, projected, pending network, price snapshot refs.  
- **Worker:** plan, region, billing quantum, committed vs useful execution time, attribution.  
- **Inference:** model, input/output tokens, rates, request cost, retries.

## Execution 3D

Restrained — no decorative flying dollar signs. Optional billing-boundary ring on worker when wired to `CostStateV1`.
