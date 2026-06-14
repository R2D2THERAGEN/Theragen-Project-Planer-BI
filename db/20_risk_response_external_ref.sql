-- db/20_risk_response_external_ref.sql
-- Risk-response authoring (post-2c): external_ref idempotency anchor on
-- pmbok.risk_response so the daily sync can author per-risk response actions.
-- bi.risk_response already exposes risk_code + owner_name (db/03) - no view change.
-- Additive - safe to re-run.
ALTER TABLE pmbok.risk_response ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;
