"""Claim-bounded adversarial search loop."""

from __future__ import annotations

import hashlib
import json
import random
import time
from typing import Any, Callable, Protocol
from uuid import uuid4

from ghostrange_contracts.adversarial_m8 import (
    AdversarialClaimPhase,
    AdversarialVerificationReportV1,
    CounterexampleReproducibility,
    CounterexampleV1,
    MinimalityLevel,
    SearchArmKind,
    SearchArmV1,
    SearchCandidateV1,
    SearchPolicyId,
    SearchStopReason,
)

from .confirm import confirm_counterexample
from .minimize import minimize_sequence
from .mutations import generate_candidates
from .novelty import NoveltyTracker
from .oracle import evaluate_oracle
from .policies import select_arm
from .safety import SearchSafetyError, assert_candidate_in_range
from .search_memory import SearchMemory


class WorldExecutor(Protocol):
    def execute(self, action_sequence: list[dict[str, Any]]) -> dict[str, Any]: ...


def run_adversarial_search(
    plan,
    executor: WorldExecutor,
    *,
    rng: random.Random | None = None,
    candidate_stream: Callable[..., Any] | None = None,
) -> AdversarialVerificationReportV1:
    rng = rng or random.Random(42)
    search_run_id = uuid4()
    memory = SearchMemory(search_run_id)
    novelty_tracker = NoveltyTracker()
    arms = {k: SearchArmV1(kind=k, priority_weight=1.0) for k in plan.enabled_arms}
    authorized = set(plan.authorized_asset_ids)
    budget = plan.budget

    pool = list(
        candidate_stream(plan.authorized_asset_ids[0], plan.enabled_arms)
        if candidate_stream
        else generate_candidates(world_asset_id=plan.authorized_asset_ids[0], arms=plan.enabled_arms)
    )
    rr_idx = [0]
    attempts = 0
    cost = 0.0
    t0 = time.perf_counter()
    counterexamples: list[CounterexampleV1] = []
    unconfirmed = 0
    stop = SearchStopReason.BUDGET_EXHAUSTED
    phase = AdversarialClaimPhase.ADVERSARIAL_TESTING

    while attempts < budget.max_attempts and (time.perf_counter() - t0) < budget.max_wall_time_sec:
        arm_kind = select_arm(plan.search_policy, list(arms.values()), rng=rng, round_robin_index=rr_idx)
        arm = arms[arm_kind]
        batch = [c for c in pool if c.arm == arm_kind and not memory.seen(c.fingerprint)]
        if not batch:
            batch = [c for c in pool if not memory.seen(c.fingerprint)]
        if not batch:
            stop = SearchStopReason.STRATEGIES_EXHAUSTED
            break

        candidate = rng.choice(batch)
        attempts += 1
        arm.attempts += 1
        cost += 0.001

        try:
            assert_candidate_in_range(
                candidate,
                authorized_asset_ids=authorized,
                max_sequence_length=budget.max_sequence_length,
            )
        except SearchSafetyError:
            memory.record(candidate.fingerprint, candidate.arm, "REJECTED_SAFETY", "n/a")
            continue

        observation = _run_sequence(executor, candidate.action_sequence)
        obs_digest = hashlib.sha256(json.dumps(observation, sort_keys=True).encode()).hexdigest()
        nov = novelty_tracker.score(observation)
        if nov.is_novel:
            arm.novel_observations += 1

        oracle_result = evaluate_oracle(plan.oracle, observation)
        memory.record(candidate.fingerprint, candidate.arm, "oracle_checked", obs_digest, novelty=nov)

        if not oracle_result.satisfied:
            continue

        unconfirmed += 1

        def still_falsifies(seq: list[dict[str, Any]]) -> bool:
            obs = _run_sequence(executor, seq)
            return evaluate_oracle(plan.oracle, obs).satisfied

        minimized, minimality = minimize_sequence(candidate.action_sequence, still_falsifies=still_falsifies)
        repro = confirm_counterexample(
            minimized,
            execute_fresh_world=lambda seq: _run_sequence(executor, seq),
            oracle_satisfied=lambda obs: evaluate_oracle(plan.oracle, obs).satisfied,
            runs=budget.confirmation_runs,
        )

        if repro != CounterexampleReproducibility.CONFIRMED:
            continue

        arm.counterexamples += 1
        ce = CounterexampleV1(
            claim_id=plan.claim_id,
            world_id=plan.world_id,
            search_run_id=search_run_id,
            action_sequence=minimized,
            observations=observation,
            violated_invariant=plan.falsification_condition.machine_check,
            claim_contradiction=plan.falsification_condition.description,
            reproducibility=repro,
            minimality=minimality,
            original_complexity=len(candidate.action_sequence),
            minimized_complexity=len(minimized),
            confidence=0.9,
            discovered_by=candidate.arm,
            search_strategy=plan.search_policy,
            search_budget_snapshot=budget,
        )
        counterexamples.append(ce)
        phase = AdversarialClaimPhase.COUNTEREXAMPLE_FOUND
        stop = SearchStopReason.COUNTEREXAMPLE_CONFIRMED
        break

    runtime = time.perf_counter() - t0
    if not counterexamples and stop == SearchStopReason.BUDGET_EXHAUSTED:
        phase = AdversarialClaimPhase.SURVIVED_BUDGET

    return AdversarialVerificationReportV1(
        claim_id=plan.claim_id,
        search_run_id=search_run_id,
        phase=phase,
        budget=budget,
        search_policy=plan.search_policy,
        attempts=attempts,
        worlds_used=1,
        coverage_summary={a.kind.value: float(a.attempts) for a in arms.values()},
        counterexamples=counterexamples,
        unconfirmed_findings=unconfirmed,
        cost_usd=cost,
        runtime_sec=runtime,
        stop_reason=stop,
        limitations=[
            "Search bounded to enabled arms and authorized assets only.",
            "Absence of counterexample is not proof of security.",
        ],
    )


def _run_sequence(executor: WorldExecutor, sequence: list[dict[str, Any]]) -> dict[str, Any]:
    last: dict[str, Any] = {}
    for step in sequence:
        last = executor.execute(step)
    return last


__all__ = ["run_adversarial_search", "WorldExecutor"]
