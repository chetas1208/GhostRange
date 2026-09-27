"""Canonical USD representation — integer microdollars only."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

MICROS_PER_USD = 1_000_000


def usd_to_micros(amount_usd: str | Decimal) -> int:
    d = Decimal(str(amount_usd))
    micros = (d * MICROS_PER_USD).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    if micros < 0:
        raise ValueError("amount must be >= 0")
    return int(micros)


def micros_to_usd_decimal(micros: int) -> Decimal:
    if micros < 0:
        raise ValueError("micros must be >= 0")
    return Decimal(micros) / MICROS_PER_USD


def format_usd_display(micros: int, *, min_sig_below_one: bool = True) -> str:
    """Display helper — not authoritative storage."""
    if micros == 0:
        return "$0.00"
    d = micros_to_usd_decimal(micros)
    if d >= 1:
        return f"${d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"
    if min_sig_below_one:
        # avoid showing sub-cent spend as $0.00
        s = format(d, "f").rstrip("0").rstrip(".")
        return f"${s}"
    return f"${d.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)}"


def add_micros(*values: int) -> int:
    total = 0
    for v in values:
        if v < 0:
            raise ValueError("negative micros")
        total += v
    return total
