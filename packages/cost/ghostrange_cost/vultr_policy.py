"""Versioned Vultr billing policy — pinned from official docs at retrieve time."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class VultrProductClass(str, Enum):
    CLOUD_COMPUTE_STANDARD = "cloud_compute_standard"  # 672h cap
    CLOUD_GPU = "cloud_gpu"  # 730h cap
    VX1 = "vx1"  # 730h, actual hours in month
    SERVERLESS_INFERENCE = "serverless_inference"
    MOCK = "mock"


@dataclass(frozen=True)
class VultrBillingPolicySnapshot:
    """Pinned policy — update version when Vultr changes rules."""

    policy_version: str
    retrieved_at: str  # ISO date
    sources: tuple[str, ...]
    minimum_billing_unit_seconds: int
    stopped_instance_billed_until_destroyed: bool
    billing_starts_at_deploy: bool
    monthly_cap_hours_standard: int
    monthly_cap_hours_gpu: int

    @staticmethod
    def vultr_docs_2025_12_16() -> VultrBillingPolicySnapshot:
        return VultrBillingPolicySnapshot(
            policy_version="vultr_server_billing_2025-12-16",
            retrieved_at="2025-12-16",
            sources=(
                "https://docs.vultr.com/support/platform/billing/how-am-i-billed-for-my-servers",
                "https://docs.vultr.com/support/platform/billing/are-stopped-instances-still-billed-on-vultr",
                "https://www.vultr.com/resources/faq/",
            ),
            minimum_billing_unit_seconds=3600,
            stopped_instance_billed_until_destroyed=True,
            billing_starts_at_deploy=True,
            monthly_cap_hours_standard=672,
            monthly_cap_hours_gpu=730,
        )


DEFAULT_VULTR_POLICY = VultrBillingPolicySnapshot.vultr_docs_2025_12_16()
