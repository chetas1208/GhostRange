# Federated Analytics (M13)

Implemented in `federated_analytics.cohort_validation_rate`:

- Requires **minimum cohort** before release (`MINIMUM_COHORT_NOT_MET` otherwise).
- Optional **Laplace noisy count** via `differential_privacy.noisy_count` (real epsilon parameter — not fake).

Secure sum prototype: `secure_aggregation.secure_sum` (pedagogical masks).

Coordinator must not require raw incident lists.
