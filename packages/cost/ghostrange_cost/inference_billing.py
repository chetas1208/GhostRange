"""Serverless inference — token-metered, model-specific snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from ghostrange_cost.money import usd_to_micros


@dataclass(frozen=True)
class InferenceCostResult:
    input_usd_micros: int
    output_usd_micros: int
    total_usd_micros: int
    model: str
    price_snapshot_id: str | None


def inference_cost_usd_micros(
    *,
    model: str,
    input_tokens: int,
    output_tokens: int,
    input_price_per_million_usd: str | None,
    output_price_per_million_usd: str | None,
    price_snapshot_id: str | None = None,
) -> InferenceCostResult | None:
    if input_price_per_million_usd is None or output_price_per_million_usd is None:
        return None
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("token counts must be >= 0")
    in_rate = Decimal(str(input_price_per_million_usd))
    out_rate = Decimal(str(output_price_per_million_usd))
    million = Decimal("1000000")
    in_cost = (Decimal(input_tokens) * in_rate / million).quantize(Decimal("0.000001"), ROUND_HALF_UP)
    out_cost = (Decimal(output_tokens) * out_rate / million).quantize(Decimal("0.000001"), ROUND_HALF_UP)
    in_micros = usd_to_micros(in_cost)
    out_micros = usd_to_micros(out_cost)
    return InferenceCostResult(
        input_usd_micros=in_micros,
        output_usd_micros=out_micros,
        total_usd_micros=in_micros + out_micros,
        model=model,
        price_snapshot_id=price_snapshot_id,
    )
