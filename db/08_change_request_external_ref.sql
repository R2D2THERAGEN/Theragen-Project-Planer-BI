-- db/08_change_request_external_ref.sql
-- Idempotency anchor for M365-authored change requests: the SharePoint List
-- item id stored as external_ref lets the sync loop upsert each CR without
-- duplicates across runs. UNIQUE enforces one DB row per List item.
ALTER TABLE pmbok.change_request ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;
