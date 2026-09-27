# M15 benchmark artifacts

Store outputs under:

- `simulation/` — discrete-event runs  
- `baselines/` — FIFO, HEFT-like, etc.  
- `oracle/` — small DAG optimal reference  
- `cpu-gpu/` — crossover sweeps (sim default)  
- `parallelism/` — fan-out/fan-in  
- `speculation/` — waste vs win  
- `elasticity/` — scale policies  
- `quality-cost/` — diminishing returns  
- `failures/` — chaos injections  
- `live/` — **only** controlled Vultr campaigns with cost estimate recorded  

Label every artifact `SIMULATED`, `CONTROLLED_LIVE`, or `LIVE`.
