-- db/07_activity_external_ref.sql
-- Idempotency anchor for M365-authored schedule activities: the SharePoint List
-- item id. WBS elements need none - they are derived and keyed deterministically
-- by uuid5 over (project_code, workstream[, workpackage]).
ALTER TABLE pmbok.schedule_activity ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;
