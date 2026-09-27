"""Inference request cost from provider usage metadata."""

from __future__ import annotations

from typing import Any, Optional, Tuple

from ghostrange_cost.inference_billing import inference_cost_usd_micros
from ghostrange_cost.inference_defaults import VULTR_INFERENCE_FALLBACK_MIXTRAL
from ghostrange_cost.money import micros_to_usd_decimal, usd_to_micros

_FLAT_RESERVE_USD = "0.05"


def reserve_usd_micros_for_call() -> int:
    """Conservative pre-authorization when token usage unknown."""
    return usd_to_micros(_FLAT_RESERVE_USD)


def actual_usd_micros_from_response(model: str, response: dict[str, Any] | None) -> Tuple[int, str]:
    """
    Returns (micros, basis).
    basis: METERED_TOKENS | FLAT_ESTIMATE_RESERVE | PRICE_UNKNOWN
    """
    if not response:
        return reserve_usd_micros_for_call(), "FLAT_ESTIMATE_RESERVE"
    usage = response.get("usage")
    if not isinstance(usage, dict):
        return reserve_usd_micros_for_call(), "FLAT_ESTIMATE_RESERVE"
    in_t = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    out_t = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    fb = VULTR_INFERENCE_FALLBACK_MIXTRAL
    rates_model = model or fb.model
    if in_t == 0 and out_t == 0:
        return reserve_usd_micros_for_call(), "FLAT_ESTIMATE_RESERVE"
    result = inference_cost_usd_micros(
        model=rates_model,
        input_tokens=in_t,
        output_tokens=out_t,
        input_price_per_million_usd=fb.input_per_million_usd,
        output_price_per_million_usd=fb.output_per_million_usd,
    )
    if result is None:
        return 0, "PRICE_UNKNOWN"
    return result.total_usd_micros, "METERED_TOKENS"


def micros_to_float_usd(micros: int) -> float:
    return float(micros_to_usd_decimal(micros))
