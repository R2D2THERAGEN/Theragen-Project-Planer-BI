-- ============================================================
-- bi schema: stable contracts for the Power BI semantic model.
-- Each view reproduces the column set of the original SampleData
-- CSV exactly, so the model's M renames keep working untouched.
-- Derived columns the OLTP schema doesn't store (cycle_time_days,
-- report_number, *_name denormalizations) are computed here.
-- ============================================================
CREATE SCHEMA IF NOT EXISTS bi;

CREATE OR REPLACE VIEW bi.department AS
SELECT department_id, code, name, active
FROM doc_mgmt.department;

CREATE OR REPLACE VIEW bi.person AS
SELECT p.person_id, p.employee_number, p.email, p.display_name,
       d.code AS department_code, d.name AS department_name,
       r.name AS role_title, p.employment_type, p.active, p.start_date
FROM doc_mgmt.person p
JOIN doc_mgmt.department d USING (department_id)
LEFT JOIN doc_mgmt.role r USING (role_id);

CREATE OR REPLACE VIEW bi.project AS
SELECT pr.project_id, pr.project_code, pr.intake_id, pr.name, pr.description,
       ch.business_case AS business_value,
       pr.sponsor_person_id, sp.display_name AS sponsor_name,
       pr.project_manager_id, pm.display_name AS project_manager_name,
       pr.primary_department, pr.approach, pr.lifecycle_phase, pr.status,
       pr.planned_start, pr.planned_finish, pr.actual_start, pr.actual_finish,
       pr.budget_total, pr.strategic_objective_ref
FROM pmbok.project pr
JOIN doc_mgmt.person sp ON sp.person_id = pr.sponsor_person_id
JOIN doc_mgmt.person pm ON pm.person_id = pr.project_manager_id
LEFT JOIN pmbok.project_charter ch ON ch.project_id = pr.project_id;

CREATE OR REPLACE VIEW bi.wbs_element AS
SELECT w.wbs_element_id, w.project_id, p.project_code, w.wbs_code,
       w.parent_wbs_element_id, w.level, w.name, w.owning_department,
       w.owner_role, w.estimated_effort_hrs, w.estimated_cost
FROM pmbok.wbs_element w
JOIN pmbok.project p USING (project_id);

CREATE OR REPLACE VIEW bi.schedule_activity AS
SELECT a.activity_id, a.wbs_element_id, w.project_id, p.project_code,
       a.activity_code, a.name, a.start_planned, a.finish_planned,
       a.start_actual, a.finish_actual, a.duration_days,
       a.owner_person_id, pe.display_name AS owner_name,
       a.department, a.status, a.pct_complete
FROM pmbok.schedule_activity a
JOIN pmbok.wbs_element w USING (wbs_element_id)
JOIN pmbok.project p ON p.project_id = w.project_id
JOIN doc_mgmt.person pe ON pe.person_id = a.owner_person_id;

CREATE OR REPLACE VIEW bi.milestone AS
SELECT m.milestone_id, m.project_id, p.project_code, m.name,
       m.baseline_date, m.forecast_date, m.actual_date, m.status, m.owner_role
FROM pmbok.milestone m
JOIN pmbok.project p USING (project_id);

CREATE OR REPLACE VIEW bi.budget_line_item AS
SELECT b.budget_line_id, b.wbs_element_id, w.project_id, p.project_code,
       w.wbs_code, w.name AS wbs_name, b.category,
       b.labor_amount, b.materials_amount, b.vendor_amount, b.other_amount,
       b.subtotal, b.contingency_pct, b.total, b.funding_source
FROM pmbok.budget_line_item b
JOIN pmbok.wbs_element w USING (wbs_element_id)
JOIN pmbok.project p ON p.project_id = w.project_id;

CREATE OR REPLACE VIEW bi.risk AS
SELECT r.risk_id, r.project_id, p.project_code, r.risk_code, r.category,
       r.description, r."trigger", r.likelihood, r.impact, r.score,
       r.response_type, r.owner_person_id, pe.display_name AS owner_name,
       r.department, r.due_date, r.status, r.residual_score, r.compliance_flag
FROM pmbok.risk r
JOIN pmbok.project p USING (project_id)
JOIN doc_mgmt.person pe ON pe.person_id = r.owner_person_id;

CREATE OR REPLACE VIEW bi.risk_response AS
SELECT rr.response_id, rr.risk_id, p.project_code, r.risk_code,
       rr.action_type, rr.description, rr.owner_person_id,
       pe.display_name AS owner_name, rr.due_date, rr.status
FROM pmbok.risk_response rr
JOIN pmbok.risk r USING (risk_id)
JOIN pmbok.project p ON p.project_id = r.project_id
JOIN doc_mgmt.person pe ON pe.person_id = rr.owner_person_id;

CREATE OR REPLACE VIEW bi.change_request AS
SELECT c.cr_id, c.project_id, p.project_code, c.cr_code, c.intake_id,
       c.requested_at, c.requested_by_person_id,
       pe.display_name AS requested_by_name, c.cr_class, c.change_types,
       c.description, c.reason, c.impact_schedule_days, c.impact_cost,
       c.decision, c.decided_at,
       (c.decided_at - c.requested_at) AS cycle_time_days,
       c.status
FROM pmbok.change_request c
JOIN pmbok.project p USING (project_id)
JOIN doc_mgmt.person pe ON pe.person_id = c.requested_by_person_id;

CREATE OR REPLACE VIEW bi.status_report AS
SELECT s.report_id, s.project_id, p.project_code,
       ROW_NUMBER() OVER (PARTITION BY s.project_id ORDER BY s.period_start)
           AS report_number,
       s.period_start, s.period_end, s.overall_status, s.trend,
       s.executive_summary, s.decisions_needed,
       s.submitted_by_person_id, pe.display_name AS submitted_by_name,
       s.submitted_at::date AS submitted_at
FROM pmbok.status_report s
JOIN pmbok.project p USING (project_id)
JOIN doc_mgmt.person pe ON pe.person_id = s.submitted_by_person_id;

CREATE OR REPLACE VIEW bi.status_report_area AS
SELECT a.area_id, a.report_id, p.project_code, a.knowledge_area,
       a.status, a.commentary
FROM pmbok.status_report_area a
JOIN pmbok.status_report s USING (report_id)
JOIN pmbok.project p ON p.project_id = s.project_id;

CREATE OR REPLACE VIEW bi.stakeholder AS
SELECT s.stakeholder_id, s.project_id, p.project_code, s.stk_code,
       s.person_id, COALESCE(pe.display_name, s.group_name) AS stakeholder_name,
       s.role, s.department, s.engagement, s.interest, s.influence,
       s.communication_preference
FROM pmbok.stakeholder s
JOIN pmbok.project p USING (project_id)
LEFT JOIN doc_mgmt.person pe ON pe.person_id = s.person_id;

CREATE OR REPLACE VIEW bi.project_team_member AS
SELECT t.team_member_id, t.project_id, p.project_code, t.person_id,
       pe.display_name AS member_name, t.role, t.department,
       t.allocation_pct, t.start_date, t.end_date
FROM pmbok.project_team_member t
JOIN pmbok.project p USING (project_id)
JOIN doc_mgmt.person pe ON pe.person_id = t.person_id;

CREATE OR REPLACE VIEW bi.lesson_learned AS
SELECT l.lesson_id, l.project_id, p.project_code, l.category, l.lesson,
       l.what_happened, l.recommendation, l.followup_owner_role, l.status
FROM pmbok.lesson_learned l
JOIN pmbok.project p USING (project_id);

CREATE OR REPLACE VIEW bi.closure_checklist_item AS
SELECT c.closure_item_id, c.project_id, p.project_code, c.item,
       c.owner_role, c.done, c.evidence
FROM pmbok.closure_checklist_item c
JOIN pmbok.project p USING (project_id);

CREATE OR REPLACE VIEW bi.knowledge_area AS
SELECT knowledge_area, sort_order FROM (VALUES
    ('Scope', 1), ('Schedule', 2), ('Cost', 3), ('Quality', 4), ('Risk', 5),
    ('Stakeholders', 6), ('Compliance', 7), ('Procurement', 8),
    ('Communications', 9)
) AS t(knowledge_area, sort_order);
