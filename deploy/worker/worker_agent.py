#!/usr/bin/env python3
"""Standalone worker agent (cloud-init). Outbound-only to control plane."""
import hashlib
import json
import os
import platform
import sys
import time

try:
    import httpx
except ImportError:
    os.system("pip3 install httpx")
    import httpx


def run_cpu_benchmark(iterations: int = 2_000_000) -> dict:
    started = time.perf_counter()
    acc = 0
    for i in range(iterations):
        acc = (acc + i * 2654435761) % 1_000_000_007
    duration_ms = int((time.perf_counter() - started) * 1000)
    return {
        "iterations": iterations,
        "accumulator": acc,
        "digest": hashlib.sha256(str(acc).encode()).hexdigest(),
        "duration_ms": duration_ms,
        "platform": platform.platform(),
    }


def main() -> None:
    base = os.environ["GHOSTRANGE_CONTROL_URL"].rstrip("/")
    bootstrap = os.environ["GHOSTRANGE_BOOTSTRAP_TOKEN"]
    client = httpx.Client(timeout=60.0)
    reg = client.post(f"{base}/v1/workers/register", json={"bootstrap_token": bootstrap, "capabilities": {}})
    reg.raise_for_status()
    body = reg.json()
    wid, token = body["worker_id"], body["worker_token"]
    headers = {"Authorization": f"Bearer {token}"}
    for _ in range(120):
        client.post(f"{base}/v1/workers/{wid}/heartbeat", json={"status": "READY"}, headers=headers)
        lease = client.post(f"{base}/v1/workers/{wid}/lease", headers=headers)
        if lease.status_code == 204:
            time.sleep(3)
            continue
        lease.raise_for_status()
        task = lease.json()
        tid = task["task_id"]
        client.post(f"{base}/v1/workers/{wid}/heartbeat", json={"status": "RUNNING", "current_task_id": tid}, headers=headers)
        bench = run_cpu_benchmark()
        bundle = {"benchmark.json": bench, "worker-info.json": {"hostname": platform.node()}}
        client.post(
            f"{base}/v1/workers/{wid}/tasks/{tid}/complete",
            json={"success": True, "result": bench, "artifact_bundle": bundle},
            headers=headers,
        )
        client.post(f"{base}/v1/workers/{wid}/drain", headers=headers)
        return
    sys.exit("timeout waiting for task")


if __name__ == "__main__":
    main()
