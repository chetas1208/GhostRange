-- GhostRange durable event log (ADR-011 §1: "Append the event to a durable
-- Postgres table, event_log").
--
-- Column names follow the M2 task brief literally: event_id, event_version,
-- event_type, seq, timestamp (-> occurred_at, see README "Column naming"),
-- correlation_id, range_id, world_id, source, payload jsonb.
--
-- Idempotent: safe to run against an existing database (CREATE ... IF NOT
-- EXISTS everywhere), so it can double as both the first-time bootstrap and
-- a no-op on every subsequent app/test startup.

CREATE TABLE IF NOT EXISTS event_log (
    -- Envelope identity. This is the *payload's own* event_id (every
    -- ghostrange_events.GhostRangeEvent already carries one) — not a
    -- separately-minted storage id — so a row and its in-memory typed
    -- object always agree on identity.
    event_id        UUID PRIMARY KEY,

    -- Which Range this event belongs to, and the per-range order it was
    -- durably appended in. (range_id, seq) is the ordering/idempotency key
    -- the whole replay+live-handoff design (ADR-011 §5) depends on.
    range_id        UUID NOT NULL,
    seq             BIGINT NOT NULL,

    -- Optional narrower scope (most events happen inside a World; a few
    -- range.* events do not yet have one).
    world_id        UUID NULL,

    -- What kind of event, and which version of its payload shape
    -- (EventName.value, e.g. "world.forked"; GhostRangeEvent.schema_version,
    -- currently always "1"). Both are also embedded in `payload` itself
    -- (self-describing on the wire) but are pulled out as real columns so
    -- they're indexable/filterable without a JSONB traversal.
    event_type      TEXT NOT NULL,
    event_version   TEXT NOT NULL,

    -- When the event occurred (GhostRangeEvent.occurred_at). Named
    -- occurred_at, not the bare reserved word `timestamp`, to avoid
    -- needing to quote it in every query; this is the same column the task
    -- brief calls "timestamp".
    occurred_at     TIMESTAMPTZ NOT NULL,

    -- Which producer emitted this (e.g. "range-runtime", "scheduler",
    -- "execution-graph", "apps/api"). Required — every append call must
    -- say who it is, per this package's append() signature.
    source          TEXT NOT NULL,

    -- Optional cross-event causal-chain id (e.g. one HTTP request in
    -- apps/api that results in several downstream events) — not
    -- interpreted by this package, just carried through.
    correlation_id  UUID NULL,

    -- The full, flat, self-describing event exactly as
    -- ghostrange_events.parse_event() can re-hydrate it
    -- (model_dump(mode="json") of the GhostRangeEvent subclass instance).
    payload         JSONB NOT NULL,

    appended_at     TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- The core ordering invariant: at most one event per (range_id, seq).
    CONSTRAINT event_log_range_seq_unique UNIQUE (range_id, seq)
);

-- Replay queries are always "this range, seq > N, ordered by seq" — the
-- unique constraint above already creates a btree on (range_id, seq) that
-- serves this directly, but name it explicitly so it survives if the
-- constraint implementation ever changes.
CREATE INDEX IF NOT EXISTS event_log_range_seq_idx ON event_log (range_id, seq);

-- Secondary lookup used by evidence/debugging tooling ("show me everything
-- that happened in this World"), not on the replay hot path.
CREATE INDEX IF NOT EXISTS event_log_world_idx ON event_log (world_id) WHERE world_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS event_log_correlation_idx
    ON event_log (correlation_id) WHERE correlation_id IS NOT NULL;

-- Per-range monotonic seq counter. A single-row UPDATE ... RETURNING per
-- range (see store/postgres.py's append()) is the concurrency-safe
-- assignment strategy ADR-011's "Consequences" section flags as a real
-- implementation detail: a naive `SELECT MAX(seq)+1 FROM event_log WHERE
-- range_id = ...` then INSERT is a read-then-write race under concurrent
-- appends to the same range. This table turns assignment into one atomic
-- UPSERT statement instead.
CREATE TABLE IF NOT EXISTS range_seq_counters (
    range_id  UUID PRIMARY KEY,
    next_seq  BIGINT NOT NULL DEFAULT 1
);

-- Application metadata for Object Storage blobs (bytes live in S3 only).
CREATE TABLE IF NOT EXISTS artifact_registry (
    artifact_id   UUID PRIMARY KEY,
    case_id       UUID NOT NULL,
    object_key    TEXT NOT NULL,
    sha256        CHAR(64) NOT NULL,
    mime_type     TEXT NOT NULL DEFAULT 'application/octet-stream',
    size_bytes    BIGINT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS artifact_registry_case_idx ON artifact_registry (case_id);

-- GhostScheduler ephemeral worker audit trail.
CREATE TABLE IF NOT EXISTS scheduler_worker_runs (
    run_id              UUID PRIMARY KEY,
    range_id            UUID NOT NULL,
    experiment_id       UUID NULL,
    provider            TEXT NOT NULL,
    provider_compute_id TEXT NULL,
    status              TEXT NOT NULL,
    benchmark_score     DOUBLE PRECISION NULL,
    cost_estimate_usd   DOUBLE PRECISION NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    terminated_at       TIMESTAMPTZ NULL,
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS scheduler_worker_runs_range_idx ON scheduler_worker_runs (range_id);

-- Real worker runtime (control plane authoritative; workers never touch Postgres).
CREATE TABLE IF NOT EXISTS worker_bootstrap_tokens (
    token_hash      CHAR(64) PRIMARY KEY,
    run_id          UUID NOT NULL,
    worker_id       UUID NOT NULL,
    range_id        UUID NOT NULL,
    expires_at      TIMESTAMPTZ NOT NULL,
    consumed_at     TIMESTAMPTZ NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS worker_instances (
    worker_id             UUID PRIMARY KEY,
    run_id                UUID NOT NULL REFERENCES scheduler_worker_runs(run_id),
    range_id              UUID NOT NULL,
    provider              TEXT NOT NULL,
    provider_instance_id  TEXT NULL,
    status                TEXT NOT NULL,
    worker_token_hash     CHAR(64) NULL,
    resource_class        TEXT NOT NULL DEFAULT 'cpu',
    capabilities          JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_seen_at          TIMESTAMPTZ NULL,
    expires_at            TIMESTAMPTZ NOT NULL,
    ready_at              TIMESTAMPTZ NULL,
    terminated_at         TIMESTAMPTZ NULL,
    failure_reason        TEXT NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata              JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS worker_instances_run_idx ON worker_instances (run_id);
CREATE INDEX IF NOT EXISTS worker_instances_status_idx ON worker_instances (status);

CREATE TABLE IF NOT EXISTS worker_tasks (
    task_id           UUID PRIMARY KEY,
    run_id            UUID NOT NULL,
    range_id          UUID NOT NULL,
    task_type         TEXT NOT NULL,
    payload           JSONB NOT NULL DEFAULT '{}'::jsonb,
    status            TEXT NOT NULL,
    timeout_seconds   INT NOT NULL DEFAULT 120,
    lease_seconds     INT NOT NULL DEFAULT 180,
    worker_id         UUID NULL,
    artifact_id       UUID NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at        TIMESTAMPTZ NULL,
    completed_at      TIMESTAMPTZ NULL,
    failure_reason    TEXT NULL
);

CREATE INDEX IF NOT EXISTS worker_tasks_run_idx ON worker_tasks (run_id);

CREATE TABLE IF NOT EXISTS worker_leases (
    lease_id      UUID PRIMARY KEY,
    task_id       UUID NOT NULL UNIQUE REFERENCES worker_tasks(task_id),
    worker_id     UUID NOT NULL REFERENCES worker_instances(worker_id),
    status        TEXT NOT NULL,
    issued_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at    TIMESTAMPTZ NOT NULL,
    renewed_at    TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS worker_leases_worker_idx ON worker_leases (worker_id);

-- M16 GhostRuntime durable campaign coordination (canonical state in Postgres).
CREATE TABLE IF NOT EXISTS campaign_runtime (
    campaign_id           UUID PRIMARY KEY,
    range_id              UUID NOT NULL,
    runtime_revision      BIGINT NOT NULL DEFAULT 0,
    lifecycle             TEXT NOT NULL,
    degradation           TEXT NOT NULL DEFAULT 'FULL',
    director_revision     BIGINT NOT NULL DEFAULT 0,
    scheduler_revision    BIGINT NOT NULL DEFAULT 0,
    causal_revision       BIGINT NOT NULL DEFAULT 0,
    dag_revision          BIGINT NOT NULL DEFAULT 0,
    budget_spent_usd      DOUBLE PRECISION NOT NULL DEFAULT 0,
    budget_hard_cap_usd   DOUBLE PRECISION NOT NULL,
    safe_mode             BOOLEAN NOT NULL DEFAULT false,
    state_json            JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_checkpoint_id    UUID NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS campaign_runtime_range_idx ON campaign_runtime (range_id);

CREATE TABLE IF NOT EXISTS runtime_leases (
    campaign_id           UUID PRIMARY KEY REFERENCES campaign_runtime(campaign_id),
    runtime_instance_id   TEXT NOT NULL,
    fencing_token         BIGINT NOT NULL,
    expires_at            TIMESTAMPTZ NOT NULL,
    acquired_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS runtime_side_effects (
    effect_id             UUID PRIMARY KEY,
    campaign_id           UUID NOT NULL REFERENCES campaign_runtime(campaign_id),
    idempotency_key       TEXT NOT NULL,
    idempotency_scope     TEXT NOT NULL,
    operation             TEXT NOT NULL,
    target                TEXT NOT NULL,
    intent_revision       BIGINT NOT NULL,
    status                TEXT NOT NULL,
    provider_reference    TEXT NULL,
    failure_detail        TEXT NULL,
    reconciliation_state  TEXT NULL,
    requested_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at          TIMESTAMPTZ NULL,
    UNIQUE (campaign_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS runtime_side_effects_campaign_idx ON runtime_side_effects (campaign_id, status);

CREATE TABLE IF NOT EXISTS runtime_checkpoints (
    checkpoint_id         UUID PRIMARY KEY,
    campaign_id           UUID NOT NULL REFERENCES campaign_runtime(campaign_id),
    runtime_revision      BIGINT NOT NULL,
    state_digest_sha256   CHAR(64) NOT NULL,
    state_blob_ref        TEXT NULL,
    inline_state          JSONB NULL,
    artifact_refs         JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS runtime_checkpoints_campaign_idx ON runtime_checkpoints (campaign_id, created_at DESC);

CREATE TABLE IF NOT EXISTS runtime_events (
    event_id              UUID PRIMARY KEY,
    campaign_id           UUID NOT NULL REFERENCES campaign_runtime(campaign_id),
    aggregate_id          UUID NOT NULL,
    sequence              BIGINT NOT NULL,
    event_type            TEXT NOT NULL,
    payload               JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at           TIMESTAMPTZ NOT NULL,
    schema_version        TEXT NOT NULL DEFAULT '1',
    UNIQUE (campaign_id, aggregate_id, sequence)
);

CREATE INDEX IF NOT EXISTS runtime_events_campaign_seq_idx ON runtime_events (campaign_id, sequence);

CREATE TABLE IF NOT EXISTS task_attempts (
    attempt_id            UUID PRIMARY KEY,
    campaign_id           UUID NOT NULL,
    task_id               UUID NOT NULL,
    worker_id             UUID NULL,
    attempt_number        INT NOT NULL,
    speculative           BOOLEAN NOT NULL DEFAULT false,
    status                TEXT NOT NULL,
    started_at            TIMESTAMPTZ NULL,
    completed_at          TIMESTAMPTZ NULL,
    UNIQUE (campaign_id, task_id, attempt_number)
);

CREATE TABLE IF NOT EXISTS canonical_task_results (
    task_id               UUID PRIMARY KEY,
    campaign_id           UUID NOT NULL,
    canonical_attempt_id  UUID NOT NULL REFERENCES task_attempts(attempt_id),
    artifact_id           UUID NULL,
    result_digest_sha256  CHAR(64) NULL,
    committed_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS runtime_recovery_runs (
    recovery_run_id       UUID PRIMARY KEY,
    campaign_id           UUID NOT NULL REFERENCES campaign_runtime(campaign_id),
    started_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at          TIMESTAMPTZ NULL,
    action                TEXT NOT NULL,
    reason_codes          JSONB NOT NULL DEFAULT '[]'::jsonb,
    duplicate_effects     INT NOT NULL DEFAULT 0,
    orphans_found         INT NOT NULL DEFAULT 0
);
