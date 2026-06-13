-- db/15_impact_assessment_external_ref.sql
-- Idempotency anchor for M365-authored per-department change-impact assessments:
-- the SharePoint List item id stored as external_ref lets the sync loop upsert
-- each assessment without duplicates across runs. UNIQUE enforces one DB row per
-- List item. The parent CR is resolved in the app layer by (project_id, cr_code).
ALTER TABLE pmbok.change_impact_assessment ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;
