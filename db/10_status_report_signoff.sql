-- db/10_status_report_signoff.sql
-- Sign-off extension for status reports: approved_by_person_id records who
-- approved the report; approved_at records when. Both are nullable so that
-- unsigned reports (the majority) remain valid without any backfill. No FK
-- on approved_by_person_id to avoid a hard dependency on the person table
-- during the additive migration; the sync layer resolves the person by email
-- before writing. A report is considered "signed" when approved_at is set.
ALTER TABLE pmbok.status_report ADD COLUMN IF NOT EXISTS approved_by_person_id UUID;
ALTER TABLE pmbok.status_report ADD COLUMN IF NOT EXISTS approved_at DATE;
