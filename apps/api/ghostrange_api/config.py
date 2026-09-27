from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    repo_root: Path
    range_dir: Path
    postgres_dsn: str | None
    redis_url: str | None
    live_provider: str  # mock | vultr | not_run
    golden_path_range_dir: Path
    live_enabled: bool
    max_worlds: int
    api_host: str
    api_port: int
    cors_origins: list[str]
    deploy_sha: str
    object_storage_provider: str
    s3_endpoint: str | None
    s3_access_key_id: str | None
    s3_secret_access_key: str | None
    s3_bucket: str | None
    s3_region: str | None
    s3_key_prefix: str
    inference_api_key: str | None
    inference_base_url: str
    inference_model: str
    trusted_proxy: bool
    require_durable: bool
    app_env: str
    vultr_api_key: str | None
    scheduler_live: bool
    max_active_workers: int
    max_active_compute_workers: int
    max_active_inference_workers: int
    max_active_worlds: int
    max_experiment_cost_usd: float
    max_campaign_cost_usd: float
    inference_worker_max_usd: float
    max_worker_lifetime_minutes: int
    vultr_worker_region: str
    vultr_worker_plan: str
    vultr_worker_os_id: int
    vultr_worker_vpc_id: str | None
    public_control_url: str
    local_control_url: str
    ghostshield_mode: str
    netbird_enabled: bool
    netbird_api_token: str | None
    netbird_worker_setup_key: str | None
    netbird_worker_group: str
    netbird_api_base_url: str
    netbird_enroll_timeout_s: float

    @classmethod
    def from_env(cls) -> "Settings":
        root = Path(os.environ.get("GHOSTRANGE_REPO_ROOT", Path(__file__).resolve().parents[3]))
        postgres_dsn = os.environ.get("POSTGRES_DSN") or os.environ.get("DATABASE_URL")
        if postgres_dsn and "sslmode=" not in postgres_dsn:
            sslmode = os.environ.get("DATABASE_SSLMODE", "require")
            sep = "&" if "?" in postgres_dsn else "?"
            postgres_dsn = f"{postgres_dsn}{sep}sslmode={sslmode}"
        cors = os.environ.get(
            "GHOSTRANGE_CORS_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173",
        )
        return cls(
            repo_root=root,
            range_dir=Path(os.environ.get("GHOSTRANGE_RANGE_DIR", root / "ranges/ghostrange-auth-lab-v1")),
            postgres_dsn=postgres_dsn,
            redis_url=os.environ.get("REDIS_URL"),
            live_provider=os.environ.get("GHOSTRANGE_LIVE_PROVIDER", "mock").lower(),
            golden_path_range_dir=Path(
                os.environ.get(
                    "GHOSTRANGE_GOLDEN_RANGE_DIR",
                    root / "ranges/ghostrange-auth-platform-v2",
                )
            ),
            live_enabled=os.environ.get("GHOSTRANGE_LIVE", "").lower() in ("1", "true", "yes"),
            max_worlds=int(os.environ.get("GHOSTRANGE_MAX_WORLDS", "1")),
            api_host=os.environ.get("GHOSTRANGE_API_HOST", "0.0.0.0"),
            api_port=int(os.environ.get("GHOSTRANGE_API_PORT", "8000")),
            cors_origins=[x.strip() for x in cors.split(",") if x.strip()],
            deploy_sha=os.environ.get("GHOSTRANGE_DEPLOY_SHA", "unknown"),
            object_storage_provider=os.environ.get("OBJECT_STORAGE_PROVIDER", "local").lower(),
            s3_endpoint=os.environ.get("S3_ENDPOINT"),
            s3_access_key_id=os.environ.get("S3_ACCESS_KEY_ID"),
            s3_secret_access_key=os.environ.get("S3_SECRET_ACCESS_KEY"),
            s3_bucket=os.environ.get("S3_BUCKET"),
            s3_region=os.environ.get("S3_REGION"),
            s3_key_prefix=os.environ.get("S3_KEY_PREFIX", "artifacts/"),
            inference_api_key=os.environ.get("VULTR_INFERENCE_API_KEY"),
            inference_base_url=os.environ.get(
                "VULTR_INFERENCE_BASE_URL",
                "https://api.vultrinference.com/v1",
            ),
            inference_model=os.environ.get("VULTR_INFERENCE_MODEL", "llama-3.1-8b-instruct"),
            trusted_proxy=os.environ.get("GHOSTRANGE_TRUSTED_PROXY", "").lower() in ("1", "true", "yes"),
            require_durable=os.environ.get("GHOSTRANGE_REQUIRE_DURABLE", "").lower() in ("1", "true", "yes"),
            app_env=os.environ.get("APP_ENV", "development"),
            vultr_api_key=os.environ.get("VULTR_API_KEY"),
            scheduler_live=os.environ.get("GHOSTSCHEDULER_LIVE", "").lower() in ("1", "true", "yes"),
            max_active_workers=int(os.environ.get("MAX_ACTIVE_WORKERS", "2")),
            # Deliberately does NOT fall back to legacy MAX_ACTIVE_WORKERS: an old .env with
            # only that var set (tuned for logical concurrency) must never silently grant
            # more than 1 real, billable Vultr Compute VM at a time.
            max_active_compute_workers=int(os.environ.get("MAX_ACTIVE_COMPUTE_WORKERS", "1")),
            max_active_inference_workers=int(
                os.environ.get("MAX_ACTIVE_INFERENCE_WORKERS", os.environ.get("MAX_ACTIVE_WORKERS", "2"))
            ),
            max_active_worlds=int(os.environ.get("MAX_ACTIVE_WORLDS", "3")),
            max_experiment_cost_usd=float(os.environ.get("MAX_EXPERIMENT_COST_USD", "5")),
            max_campaign_cost_usd=float(os.environ.get("MAX_CAMPAIGN_COST_USD", "25")),
            inference_worker_max_usd=float(os.environ.get("INFERENCE_WORKER_MAX_USD", "25")),
            max_worker_lifetime_minutes=int(os.environ.get("MAX_WORKER_LIFETIME_MINUTES", "45")),
            vultr_worker_region=os.environ.get("VULTR_WORKER_REGION", "lax"),
            vultr_worker_plan=os.environ.get("VULTR_WORKER_PLAN", "vc2-1c-1gb"),
            vultr_worker_os_id=int(os.environ.get("VULTR_WORKER_OS_ID", "1743")),
            vultr_worker_vpc_id=os.environ.get("GHOSTRANGE_WORKER_VPC_ID"),
            public_control_url=os.environ.get(
                "GHOSTRANGE_PUBLIC_URL",
                os.environ.get("GHOSTRANGE_CONTROL_URL", "http://127.0.0.1:8000"),
            ).rstrip("/"),
            local_control_url=os.environ.get(
                "GHOSTRANGE_LOCAL_CONTROL_URL",
                f"http://127.0.0.1:{os.environ.get('GHOSTRANGE_API_PORT', '8000')}",
            ).rstrip("/"),
            ghostshield_mode=os.environ.get("GHOSTSHIELD_MODE", "SHADOW").upper(),
            # NetBird mesh overlay (control-plane <-> worker connectivity, ephemeral worker
            # enrollment, micro-segmentation) — see packages/netbird-control and
            # ghostrange_api.netbird_gate. Fully inert (no behavior change at all) unless
            # NETBIRD_ENABLED=true; default is false, and this default must never be flipped
            # here — only an operator's own .env decides that.
            netbird_enabled=os.environ.get("NETBIRD_ENABLED", "").lower() in ("1", "true", "yes"),
            netbird_api_token=os.environ.get("NETBIRD_API_TOKEN"),
            netbird_worker_setup_key=os.environ.get("NETBIRD_WORKER_SETUP_KEY"),
            netbird_worker_group=os.environ.get("NETBIRD_WORKER_GROUP", "ghostrange-workers"),
            netbird_api_base_url=os.environ.get("NETBIRD_API_BASE_URL", "https://api.netbird.io"),
            netbird_enroll_timeout_s=float(os.environ.get("NETBIRD_ENROLL_TIMEOUT_S", "120")),
        )

    @property
    def use_postgres(self) -> bool:
        return bool(self.postgres_dsn and self.redis_url)

    @property
    def s3_configured(self) -> bool:
        return self.object_storage_provider == "vultr" and bool(
            self.s3_endpoint and self.s3_access_key_id and self.s3_secret_access_key and self.s3_bucket
        )

    @property
    def inference_configured(self) -> bool:
        return bool(self.inference_api_key)

    @property
    def netbird_configured(self) -> bool:
        """True only when NETBIRD_ENABLED=true AND the credentials it needs
        are actually present. NETBIRD_ENABLED=true with a missing token/setup
        key is a misconfiguration, not silently-disabled — callers should
        raise loudly rather than fall back to the pre-NetBird gate in that
        case (see netbird_gate.build_netbird_client)."""
        return self.netbird_enabled and bool(self.netbird_api_token) and bool(self.netbird_worker_setup_key)

    @property
    def workers_live_only(self) -> bool:
        """When true, worker benchmarks always use real Vultr (no in-process mock agent)."""
        return self.scheduler_live and bool(self.vultr_api_key) and bool(self.vultr_worker_vpc_id)

    @property
    def live_only_runtime(self) -> bool:
        """Production or explicit live+durable: no mock providers or in-memory event fallback."""
        return self.app_env == "production" or (self.live_enabled and self.require_durable)

    def validate_for_runtime(self) -> None:
        """Fail fast before binding ports — production must never start on mocks."""
        if os.environ.get("GHOSTRANGE_SKIP_RUNTIME_VALIDATE", "").lower() in ("1", "true", "yes"):
            return
        if self.require_durable and not self.use_postgres:
            raise RuntimeError(
                "GHOSTRANGE_REQUIRE_DURABLE=true requires POSTGRES_DSN and REDIS_URL (no in-memory gateway)"
            )
        if not self.live_only_runtime:
            return
        if not self.live_enabled:
            raise RuntimeError("Live-only runtime requires GHOSTRANGE_LIVE=true")
        if self.live_provider != "vultr":
            raise RuntimeError(
                f"Live-only runtime forbids GHOSTRANGE_LIVE_PROVIDER={self.live_provider!r}; use vultr"
            )
        if not self.vultr_api_key:
            raise RuntimeError("Live-only runtime requires VULTR_API_KEY")
        if not self.inference_configured:
            raise RuntimeError("Live-only runtime requires VULTR_INFERENCE_API_KEY")
        if not self.workers_live_only:
            raise RuntimeError(
                "Live-only runtime requires GHOSTSCHEDULER_LIVE=true, VULTR_API_KEY, GHOSTRANGE_WORKER_VPC_ID"
            )
        if self.object_storage_provider != "vultr" or not self.s3_configured:
            raise RuntimeError("Live-only runtime requires OBJECT_STORAGE_PROVIDER=vultr and S3 credentials")

    # Hard, code-level ceilings that no env var can raise — a misconfigured .env can only
    # make these *stricter*, never looser. Defense in depth on top of the GhostShield gateway.
    INFERENCE_WORKER_HARD_CEILING: int = 10
    INFERENCE_WORKER_BUDGET_HARD_CEILING_USD: float = 25.0

    @property
    def inference_worker_concurrency_cap(self) -> int:
        """Effective MAX_ACTIVE_INFERENCE_WORKERS for the inference worker pool, clamped to <=10.

        This is deliberately a SEPARATE knob from compute-worker concurrency: inference
        calls are logical/stateless (no VM lifecycle, no per-hour billing), so they can
        safely run at a higher cap than real billable Vultr Compute VMs ever should.
        """
        return max(1, min(self.max_active_inference_workers, self.INFERENCE_WORKER_HARD_CEILING))

    # Real Vultr Compute VMs are billable infrastructure with a VM lifecycle — no code-level
    # ceiling raises this above what MAX_ACTIVE_COMPUTE_WORKERS says, but unlike the inference
    # pool there is no "safe to raise" hard ceiling here at all: the operator's configured
    # value is authoritative, and the default is deliberately 1.
    @property
    def compute_worker_concurrency_cap(self) -> int:
        """Effective MAX_ACTIVE_COMPUTE_WORKERS for real Vultr Compute VM provisioning."""
        return max(1, self.max_active_compute_workers)

    @property
    def inference_worker_budget_cap_usd(self) -> float:
        """Effective session spend cap for the inference worker pool, clamped to <=$25."""
        return max(0.0, min(self.inference_worker_max_usd, self.INFERENCE_WORKER_BUDGET_HARD_CEILING_USD))
