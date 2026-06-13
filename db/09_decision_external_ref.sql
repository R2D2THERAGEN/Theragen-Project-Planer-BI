-- db/09_decision_external_ref.sql
-- Idempotency anchor for M365-authored project decisions: the SharePoint List
-- item id stored as external_ref lets the sync loop upsert each decision
-- without duplicates across runs. UNIQUE enforces one DB row per List item.
ALTER TABLE pmbok.decision ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;
