-- db/06_artifact_external_ref.sql
-- Idempotency anchors for M365-authored execution artifacts: each synced table
-- remembers its SharePoint List item id. One List per table, so the bare item
-- id is unique per table. status_report_area needs none - its rows are keyed
-- deterministically through their parent report.
ALTER TABLE pmbok.risk          ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;
ALTER TABLE pmbok.milestone     ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;
ALTER TABLE pmbok.status_report ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;
