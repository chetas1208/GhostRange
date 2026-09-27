# Task latency model (M4)

Contract: `TaskLatencyModelV1` + `RuntimeDistributionV1` per `TaskType`.

- Online update: exponential moving average (Agent 06, planned).
- Straggler detection: compare elapsed to class P95 × multiplier (`config/ghostscheduler-v3.yaml`).
- Simulator uses model estimates until traces from M3/M4 investigations populate distributions.
