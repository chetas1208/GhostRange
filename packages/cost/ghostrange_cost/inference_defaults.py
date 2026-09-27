"""Fallback inference price snapshot — replace via live price fetch; never $0."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InferenceRateFallback:
    model: str
    input_per_million_usd: str
    output_per_million_usd: str
    source: str
    retrieved_at: str


# Vultr docs (Mixtral example rates) — per-model snapshots required in production.
VULTR_INFERENCE_FALLBACK_MIXTRAL = InferenceRateFallback(
    model="mixtral-8x7b-instruct",
    input_per_million_usd="0.55",
    output_per_million_usd="2.75",
    source="https://docs.vultr.com/support/products/serverless/how-do-i-monitor-the-usage-and-cost-of-my-vultr-serverless-inference-subscription",
    retrieved_at="2026-03-10",
)
