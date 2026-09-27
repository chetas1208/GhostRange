"""Poll-based worker runtime — outbound only to control plane."""

from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx

from .benchmark import run_cpu_benchmark


class WorkerRuntime:
    def __init__(self, control_url: str, bootstrap_token: str) -> None:
        self.control_url = control_url.rstrip("/")
        self.bootstrap_token = bootstrap_token
        self.worker_id: str | None = None
        self.worker_token: str | None = None

    def register(self) -> None:
        payload = {
            "bootstrap_token": self.bootstrap_token,
            "hostname": os.uname().nodename,
            "capabilities": {"task_types": ["CPU_BENCHMARK"]},
        }
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(f"{self.control_url}/v1/workers/register", json=payload)
            resp.raise_for_status()
            body = resp.json()
        self.worker_id = body["worker_id"]
        self.worker_token = body["worker_token"]

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.worker_token}"}

    def heartbeat(self, *, status: str = "READY", task_id: str | None = None) -> None:
        assert self.worker_id
        with httpx.Client(timeout=15.0) as client:
            client.post(
                f"{self.control_url}/v1/workers/{self.worker_id}/heartbeat",
                json={"status": status, "current_task_id": task_id},
                headers=self._headers(),
            )

    def acquire_lease(self) -> dict[str, Any] | None:
        assert self.worker_id
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{self.control_url}/v1/workers/{self.worker_id}/lease",
                headers=self._headers(),
            )
            if resp.status_code == 204:
                return None
            resp.raise_for_status()
            return resp.json()

    def complete_task(
        self, task_id: str, *, bundle: dict[str, Any], files: dict[str, Any] | None = None
    ) -> None:
        assert self.worker_id
        artifact_bundle = files if files is not None else bundle
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{self.control_url}/v1/workers/{self.worker_id}/tasks/{task_id}/complete",
                json={"success": True, "result": bundle, "artifact_bundle": artifact_bundle},
                headers=self._headers(),
            )
            resp.raise_for_status()

    def fail_task(self, task_id: str, reason: str) -> None:
        assert self.worker_id
        with httpx.Client(timeout=30.0) as client:
            client.post(
                f"{self.control_url}/v1/workers/{self.worker_id}/tasks/{task_id}/fail",
                json={"reason": reason},
                headers=self._headers(),
            )

    def drain(self) -> None:
        assert self.worker_id
        with httpx.Client(timeout=15.0) as client:
            client.post(f"{self.control_url}/v1/workers/{self.worker_id}/drain", headers=self._headers())

    def run_until_idle(self, *, heartbeat_s: float = 10.0, poll_s: float = 3.0) -> None:
        self.register()
        deadline = time.time() + float(os.environ.get("GHOSTRANGE_WORKER_MAX_SECONDS", "600"))
        while time.time() < deadline:
            self.heartbeat(status="READY")
            lease = self.acquire_lease()
            if not lease:
                time.sleep(poll_s)
                continue
            task_id = lease["task_id"]
            task_type = lease.get("task_type")
            self.heartbeat(status="RUNNING", task_id=task_id)
            try:
                if task_type == "CPU_BENCHMARK":
                    bench = run_cpu_benchmark()
                    u = os.uname()
                    env = {"hostname": u.nodename}
                    bundle = {
                        "worker-info.json": env,
                        "benchmark.json": bench,
                        "environment.json": {
                            "sysname": u.sysname,
                            "nodename": u.nodename,
                            "release": u.release,
                            "version": u.version,
                            "machine": u.machine,
                        },
                    }
                    self.complete_task(task_id, bundle=bench, files=bundle)
                else:
                    self.fail_task(task_id, f"unsupported task_type {task_type}")
            except Exception as exc:
                self.fail_task(task_id, type(exc).__name__)
            self.drain()
            return
        raise TimeoutError("worker idle timeout waiting for lease")


def main_from_env() -> None:
    url = os.environ["GHOSTRANGE_CONTROL_URL"]
    token = os.environ["GHOSTRANGE_BOOTSTRAP_TOKEN"]
    WorkerRuntime(url, token).run_until_idle()
