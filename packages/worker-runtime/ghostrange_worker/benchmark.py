"""Deterministic CPU benchmark — no network."""

from __future__ import annotations

import hashlib
import platform
import time
from typing import Any


def run_cpu_benchmark(*, iterations: int = 2_000_000) -> dict[str, Any]:
    started = time.perf_counter()
    acc = 0
    for i in range(iterations):
        acc = (acc + i * 2654435761) % 1_000_000_007
    digest = hashlib.sha256(str(acc).encode()).hexdigest()
    duration_ms = int((time.perf_counter() - started) * 1000)
    return {
        "iterations": iterations,
        "accumulator": acc,
        "digest": digest,
        "duration_ms": duration_ms,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cpu_count": platform.processor() or "unknown",
    }
