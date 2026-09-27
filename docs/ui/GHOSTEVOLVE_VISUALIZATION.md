# GhostEvolve visualization

Three primary tabs unchanged.

Components (`packages/ui-3d/src/evolve/`):

- `EvolutionMarker` — version transition
- `ChampionPolicy` / `ChallengerPolicy` — execution paths
- `ShadowDecision` — champion vs shadow labels; challenger non-authoritative

Evidence tab (planned): lineage chain experience → candidate → offline → regression → shadow → approval → GhostShield → canary.

No fake learning animations — bind to backend state when wired.
