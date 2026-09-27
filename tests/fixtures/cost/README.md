# Cost golden vectors

Hand-calculated expected outcomes live in `packages/cost/tests/test_acceptance_examples.py`
with derivations in `packages/cost/tests/reference_calculator.py` (independent of production).

Example A (7 min VM, $P/hr, 1h minimum):

```
billable_hours = ceil(420/3600) = 1  (minimum 1)
cost = 1 * P
NOT 420/3600 * P
```
