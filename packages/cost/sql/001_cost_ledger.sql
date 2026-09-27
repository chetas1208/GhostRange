-- GhostCostLedger durable tables (Phase 2 migration stub)
-- Apply when Postgres is authoritative for campaigns.

CREATE TABLE IF NOT EXISTS price_snapshots (
  id UUID PRIMARY KEY,
  provider TEXT NOT NULL,
  product TEXT NOT NULL,
  hourly_rate_usd_micros BIGINT,
  billing_quantum TEXT NOT NULL,
  effective_at TIMESTAMPTZ NOT NULL,
  retrieved_at TIMESTAMPTZ NOT NULL,
  source TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS resource_cost_records (
  resource_id TEXT PRIMARY KEY,
  campaign_id TEXT NOT NULL,
  price_snapshot_id UUID REFERENCES price_snapshots(id),
  committed_usd_micros BIGINT NOT NULL DEFAULT 0,
  accrued_estimate_usd_micros BIGINT NOT NULL DEFAULT 0,
  final_usd_micros BIGINT,
  billing_end_state TEXT NOT NULL DEFAULT 'ACTIVE'
);

CREATE TABLE IF NOT EXISTS inference_usage_records (
  request_id TEXT PRIMARY KEY,
  campaign_id TEXT,
  model TEXT NOT NULL,
  input_tokens BIGINT NOT NULL DEFAULT 0,
  output_tokens BIGINT NOT NULL DEFAULT 0,
  calculated_usd_micros BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
