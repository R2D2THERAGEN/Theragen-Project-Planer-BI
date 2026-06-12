-- db/05_intake_external_ref.sql
-- Idempotency anchor for M365-ingested intakes: the SharePoint List item id.
ALTER TABLE doc_mgmt.intake_submission
    ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;
