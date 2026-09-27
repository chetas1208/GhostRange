"""Cost accounting contracts (USD micros, snapshots, campaign totals)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CostSemanticType(str, Enum):
    PROJECTED = "PROJECTED_COST"
    RESERVED = "RESERVED_COST"
    ACCRUED_ESTIMATE = "ACCRUED_ESTIMATE"
    PROVIDER_REPORTED = "PROVIDER_REPORTED_COST"
    INVOICED = "INVOICED_COST"


class CostConfidence(str, Enum):
    EXACT_PROVIDER_REPORTED = "EXACT_PROVIDER_REPORTED"
    EXACT_FROM_METERED_USAGE_AND_PINNED_RATE = "EXACT_FROM_METERED_USAGE_AND_PINNED_RATE"
    ESTIMATED_FROM_PROVIDER_POLICY = "ESTIMATED_FROM_PROVIDER_POLICY"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"
    PRICE_UNKNOWN = "PRICE_UNKNOWN"
    STALE_PRICE = "STALE_PRICE"


class CostCategory(str, Enum):
    PLATFORM_FIXED = "PLATFORM_FIXED"
    COMPUTE_EPHEMERAL = "COMPUTE_EPHEMERAL"
    INFERENCE = "INFERENCE"
    DATABASE_INCREMENTAL = "DATABASE_INCREMENTAL"
    OBJECT_STORAGE = "OBJECT_STORAGE"
    NETWORK_EGRESS = "NETWORK_EGRESS"
    OTHER_PROVIDER = "OTHER_PROVIDER"
    UNKNOWN = "UNKNOWN"


class BillingQuantum(str, Enum):
    ONE_HOUR_MINIMUM = "ONE_HOUR_MINIMUM"
    PER_HOUR_ACTUAL = "PER_HOUR_ACTUAL"
    PER_TOKEN = "PER_TOKEN"
    UNKNOWN = "UNKNOWN"


class PriceSnapshotV1(BaseModel):
    id: UUID
    provider: str = "vultr"
    product: str
    plan_id: Optional[str] = None
    region: Optional[str] = None
    currency: str = "USD"
    hourly_rate_usd_micros: Optional[int] = Field(default=None, ge=0)
    monthly_rate_usd_micros: Optional[int] = Field(default=None, ge=0)
    billing_quantum: BillingQuantum = BillingQuantum.ONE_HOUR_MINIMUM
    monthly_cap_hours: Optional[int] = Field(default=None, ge=0)
    effective_at: datetime
    retrieved_at: datetime
    source: str
    source_digest: Optional[str] = None
    confidence: CostConfidence = CostConfidence.ESTIMATED_FROM_PROVIDER_POLICY


class InferencePriceSnapshotV1(BaseModel):
    id: UUID
    provider: str = "vultr"
    model: str
    input_price_per_million_usd_micros: Optional[int] = Field(default=None, ge=0)
    output_price_per_million_usd_micros: Optional[int] = Field(default=None, ge=0)
    effective_at: datetime
    retrieved_at: datetime
    source: str
    confidence: CostConfidence = CostConfidence.ESTIMATED_FROM_PROVIDER_POLICY


class ResourceLifecycleTimestampsV1(BaseModel):
    create_requested_at: Optional[datetime] = None
    provider_created_at: Optional[datetime] = None
    ready_at: Optional[datetime] = None
    first_task_at: Optional[datetime] = None
    last_task_at: Optional[datetime] = None
    destroy_requested_at: Optional[datetime] = None
    provider_destroyed_at: Optional[datetime] = None
    billing_end_confirmed: bool = False


class ResourceCostRecordV1(BaseModel):
    resource_id: str
    campaign_id: Optional[str] = None
    product: str
    plan_id: Optional[str] = None
    region: Optional[str] = None
    price_snapshot_id: UUID
    lifecycle: ResourceLifecycleTimestampsV1 = Field(default_factory=ResourceLifecycleTimestampsV1)
    committed_usd_micros: int = Field(default=0, ge=0)
    accrued_estimate_usd_micros: int = Field(default=0, ge=0)
    provider_reported_usd_micros: Optional[int] = Field(default=None, ge=0)
    final_usd_micros: Optional[int] = Field(default=None, ge=0)
    billing_end_state: str = "ACTIVE"  # ACTIVE | BILLING_END_UNCONFIRMED | FINALIZED
    confidence: CostConfidence = CostConfidence.ESTIMATED_FROM_PROVIDER_POLICY


class CostAttributionV1(BaseModel):
    resource_id: str
    task_id: str
    policy: str = "WALL_TIME_SHARE"
    attributed_usd_micros: int = Field(..., ge=0)


class InferenceUsageRecordV1(BaseModel):
    request_id: str
    campaign_id: Optional[str] = None
    model: str
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    price_snapshot_id: Optional[UUID] = None
    calculated_usd_micros: Optional[int] = Field(default=None, ge=0)
    provider_reported_usd_micros: Optional[int] = Field(default=None, ge=0)
    status: str = "COMPLETED"


class CampaignCostV1(BaseModel):
    campaign_id: str
    semantic_type: CostSemanticType = CostSemanticType.ACCRUED_ESTIMATE
    confidence: CostConfidence = CostConfidence.PARTIAL
    categories: dict[str, int] = Field(default_factory=dict)  # category -> usd_micros
    unknown_components: list[str] = Field(default_factory=list)
    total_known_usd_micros: int = Field(default=0, ge=0)
    total_projected_usd_micros: Optional[int] = Field(default=None, ge=0)
    total_provider_reported_usd_micros: Optional[int] = Field(default=None, ge=0)
    total_final_usd_micros: Optional[int] = Field(default=None, ge=0)
    finalized: bool = False
    price_snapshot_ids: list[UUID] = Field(default_factory=list)


class CostReservationV1(BaseModel):
    reservation_id: UUID
    campaign_id: str
    reserved_usd_micros: int = Field(..., ge=0)
    reason: str
    expires_at: Optional[datetime] = None


class CostStateV1(BaseModel):
    resource_id: str
    committed_usd_micros: int = 0
    accrued_estimate_usd_micros: int = 0
    incremental_to_next_boundary_usd_micros: int = 0
    projected_completion_usd_micros: Optional[int] = None
    provider_reported_usd_micros: Optional[int] = None
    final_usd_micros: Optional[int] = None
    seconds_to_next_billing_boundary: Optional[int] = None


class CampaignCostSnapshotEventV1(BaseModel):
    """Payload for SSE cost.snapshot.updated."""

    campaign_id: str
    snapshot: CampaignCostV1
