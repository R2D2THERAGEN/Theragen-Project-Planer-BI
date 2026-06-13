-- ============================================================
-- bi governance views: Task 7 of Phase 2b
-- Widens bi.change_request + bi.status_report;
-- adds bi.decision + bi.change_impact_assessment.
-- All statements are CREATE OR REPLACE — purely additive, safe to
-- re-run, and do not affect any existing column positions.
-- ============================================================

-- 1. Widen bi.change_request
--    Adds: decided_by_person_id, decided_by_name (LEFT JOIN — nullable),
--          impact_scope, impact_quality, affected_artifacts,
--          implementation_verified, linked_artifacts_updated.
CREATE OR REPLACE VIEW bi.change_request AS
SELECT c.cr_id, c.project_id, p.project_code, c.cr_code, c.intake_id,
       c.requested_at, c.requested_by_person_id,
       pe.display_name AS requested_by_name, c.cr_class, c.change_types,
       c.description, c.reason, c.impact_schedule_days, c.impact_cost,
       c.decision, c.decided_at,
       (c.decided_at - c.requested_at) AS cycle_time_days,
       c.status,
       c.decided_by_person_id,
       pd.display_name AS decided_by_name,
       c.impact_scope,
       c.impact_quality,
       c.affected_artifacts,
       c.implementation_verified,
       c.linked_artifacts_updated
FROM pmbok.change_request c
JOIN pmbok.project p USING (project_id)
JOIN doc_mgmt.person pe ON pe.person_id = c.requested_by_person_id
LEFT JOIN doc_mgmt.person pd ON pd.person_id = c.decided_by_person_id;

-- 2. Widen bi.status_report
--    Adds: approved_by_person_id, approved_by_name (LEFT JOIN — nullable),
--          approved_at, is_signed_off.
CREATE OR REPLACE VIEW bi.status_report AS
SELECT s.report_id, s.project_id, p.project_code,
       ROW_NUMBER() OVER (PARTITION BY s.project_id ORDER BY s.period_start)
           AS report_number,
       s.period_start, s.period_end, s.overall_status, s.trend,
       s.executive_summary, s.decisions_needed,
       s.submitted_by_person_id, pe.display_name AS submitted_by_name,
       s.submitted_at::date AS submitted_at,
       s.approved_by_person_id,
       pa.display_name AS approved_by_name,
       s.approved_at,
       (s.approved_at IS NOT NULL) AS is_signed_off
FROM pmbok.status_report s
JOIN pmbok.project p USING (project_id)
JOIN doc_mgmt.person pe ON pe.person_id = s.submitted_by_person_id
LEFT JOIN doc_mgmt.person pa ON pa.person_id = s.approved_by_person_id;

-- 3. New view: bi.decision
CREATE OR REPLACE VIEW bi.decision AS
SELECT d.decision_id, d.project_id, p.project_code,
       d.code, d.decision, d.rationale,
       d.decided_by_person_id,
       pe.display_name AS decided_by_name,
       d.decided_at
FROM pmbok.decision d
JOIN pmbok.project p USING (project_id)
JOIN doc_mgmt.person pe ON pe.person_id = d.decided_by_person_id;

-- 4. New view: bi.change_impact_assessment
CREATE OR REPLACE VIEW bi.change_impact_assessment AS
SELECT a.impact_id, a.cr_id, c.cr_code, p.project_code,
       a.department, a.scope_impact, a.schedule_impact_days,
       a.cost_impact, a.quality_impact,
       a.submitted_by_person_id,
       pe.display_name AS submitted_by_name,
       a.submitted_at
FROM pmbok.change_impact_assessment a
JOIN pmbok.change_request c USING (cr_id)
JOIN pmbok.project p ON p.project_id = c.project_id
JOIN doc_mgmt.person pe ON pe.person_id = a.submitted_by_person_id;
