"""Worker/task contracts (control plane)."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class WorkerLifecycle(str, Enum):
    REQUESTED = "REQUESTED"
    PROVISIONING = "PROVISIONING"
    BOOTSTRAPPING = "BOOTSTRAPPING"
    REGISTERING = "REGISTERING"
    READY = "READY"
    LEASED = "LEASED"
    RUNNING = "RUNNING"
    UPLOADING = "UPLOADING"
    COMPLETED = "COMPLETED"
    DRAINING = "DRAINING"
    TERMINATING = "TERMINATING"
    TERMINATED = "TERMINATED"
    BOOT_FAILED = "BOOT_FAILED"
    REGISTRATION_FAILED = "REGISTRATION_FAILED"
    # Vultr VM booted + GhostRange worker registered, but the NetBird mesh
    # enrollment step (peer connected AND a member of NETBIRD_WORKER_GROUP)
    # never completed within the readiness-gate timeout. Only reachable
    # when NETBIRD_ENABLED=true — see netbird_gate.py. The worker is
    # terminated when this is raised (same teardown path as any other
    # readiness-gate failure), never left running half-enrolled.
    BOOTSTRAP_FAILED = "BOOTSTRAP_FAILED"
    TASK_FAILED = "TASK_FAILED"
    ORPHANED = "ORPHANED"


class WorkerTaskType(str, Enum):
    CPU_BENCHMARK = "CPU_BENCHMARK"


class WorkerRegisterRequest(BaseModel):
    bootstrap_token: str = Field(..., min_length=16, max_length=256)
    provider_instance_id: str | None = None
    hostname: str | None = None
    capabilities: dict[str, Any] = Field(default_factory=dict)


class WorkerHeartbeatRequest(BaseModel):
    status: str = "READY"
    current_task_id: str | None = None


class WorkerTaskCompleteRequest(BaseModel):
    success: bool = True
    result: dict[str, Any] = Field(default_factory=dict)
    artifact_bundle: dict[str, Any] = Field(default_factory=dict)
    stdout: str | None = None


class WorkerTaskFailRequest(BaseModel):
    reason: str
    detail: dict[str, Any] = Field(default_factory=dict)
