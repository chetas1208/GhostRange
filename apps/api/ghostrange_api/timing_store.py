"""Historical operation timing samples + percentile summaries."""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


@dataclass(frozen=True, slots=True)
class TimingSummary:
    operation_type: str
    sample_count: int
    last_ms: Optional[int]
    min_ms: Optional[int]
    max_ms: Optional[int]
    p50_ms: Optional[int]
    p90_ms: Optional[int]
    p95_ms: Optional[int]
    estimate_confidence: str

    def to_json(self) -> dict[str, Any]:
        return {
            "operation_type": self.operation_type,
            "sample_count": self.sample_count,
            "last_ms": self.last_ms,
            "min_ms": self.min_ms,
            "max_ms": self.max_ms,
            "p50_ms": self.p50_ms,
            "p90_ms": self.p90_ms,
            "p95_ms": self.p95_ms,
            "estimate_confidence": self.estimate_confidence,
        }


def _percentile(sorted_vals: list[int], pct: float) -> Optional[int]:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * pct
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return int(sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f))


class OperationTimingStore:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def record(
        self,
        *,
        range_id: UUID | str,
        operation_type: str,
        elapsed_ms: int,
        provider: str | None = None,
        region: str | None = None,
        resource_class: str | None = None,
        task_class: str | None = None,
        queued_at: datetime | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        success: bool = True,
        failure_type: str | None = None,
    ) -> None:
        async with self._pool.connection() as conn:
            await conn.execute(
                """
                INSERT INTO operation_timing_samples (
                  range_id, operation_type, provider, region, resource_class, task_class,
                  queued_at, started_at, finished_at, elapsed_ms, success, failure_type
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    str(range_id),
                    operation_type,
                    provider,
                    region,
                    resource_class,
                    task_class,
                    queued_at,
                    started_at,
                    finished_at or datetime.now(timezone.utc),
                    elapsed_ms,
                    success,
                    failure_type,
                ),
            )

    async def summary(
        self,
        operation_type: str,
        *,
        provider: str | None = None,
        region: str | None = None,
        limit: int = 500,
    ) -> TimingSummary:
        clauses = ["operation_type = %s", "success = TRUE"]
        params: list[Any] = [operation_type]
        if provider:
            clauses.append("provider = %s")
            params.append(provider)
        if region:
            clauses.append("region = %s")
            params.append(region)
        where = " AND ".join(clauses)
        async with self._pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    f"""
                    SELECT elapsed_ms FROM operation_timing_samples
                    WHERE {where}
                    ORDER BY recorded_at DESC
                    LIMIT %s
                    """,
                    (*params, limit),
                )
                rows = await cur.fetchall()
        vals = [int(r["elapsed_ms"]) for r in rows]
        n = len(vals)
        conf = "LOW_SAMPLE_COUNT" if n < 5 else ("MEDIUM" if n < 20 else "HIGH")
        sorted_vals = sorted(vals)
        return TimingSummary(
            operation_type=operation_type,
            sample_count=n,
            last_ms=vals[0] if vals else None,
            min_ms=min(vals) if vals else None,
            max_ms=max(vals) if vals else None,
            p50_ms=_percentile(sorted_vals, 0.5),
            p90_ms=_percentile(sorted_vals, 0.9),
            p95_ms=_percentile(sorted_vals, 0.95),
            estimate_confidence=conf,
        )

    def estimate_remaining(
        self,
        summary: TimingSummary,
        elapsed_ms: int,
        *,
        basis: str = "HISTORICAL_P50",
    ) -> dict[str, Any]:
        if summary.sample_count < 5:
            return {
                "estimated_total_ms": None,
                "estimated_remaining_ms": None,
                "estimate_basis": "INSUFFICIENT_DATA",
                "sample_count": summary.sample_count,
            }
        target = summary.p50_ms if basis == "HISTORICAL_P50" else summary.p95_ms
        if target is None:
            return {
                "estimated_total_ms": None,
                "estimated_remaining_ms": None,
                "estimate_basis": "INSUFFICIENT_DATA",
                "sample_count": summary.sample_count,
            }
        remaining = max(0, target - elapsed_ms)
        return {
            "estimated_total_ms": target,
            "estimated_remaining_ms": remaining,
            "estimate_basis": basis,
            "sample_count": summary.sample_count,
        }
