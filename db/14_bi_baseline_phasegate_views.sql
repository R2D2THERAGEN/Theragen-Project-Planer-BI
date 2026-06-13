-- ============================================================
-- bi baseline + phase-gate views: Task 7 of Phase 2c-1
-- Adds bi.project_baseline + bi.phase_gate_log — stable contracts
-- for the Power BI semantic model over pmbok.project_baseline and
-- pmbok.phase_gate_log. The snapshot JSONB is summarized into two
-- scalar columns (baseline_budget_total, baseline_activity_count)
-- so the model never has to parse JSON.
-- Both statements are CREATE OR REPLACE — purely additive, safe to
-- re-run, and do not affect any existing column positions.
-- ============================================================

-- 1. New view: bi.project_baseline
--    baseline_budget_total / baseline_activity_count are derived from
--    the frozen snapshot JSONB (null/0 when the type has no such facet).
--    LEFT JOIN person — baselined_by_person_id is nullable.
CREATE OR REPLACE VIEW bi.project_baseline AS
SELECT b.baseline_id, b.project_id, p.project_code,
       b.baseline_type, b.version, b.status,
       b.change_summary, b.change_class,
       b.baselined_at, b.baselined_by_person_id,
       pe.display_name AS baselined_by_name,
       (b.snapshot->>'budget_total')::numeric AS baseline_budget_total,
       jsonb_array_length(COALESCE(b.snapshot->'activities', '[]'::jsonb))
           AS baseline_activity_count,
       b.linked_cr_id
FROM pmbok.project_baseline b
JOIN pmbok.project p USING (project_id)
LEFT JOIN doc_mgmt.person pe ON pe.person_id = b.baselined_by_person_id;

-- 2. New view: bi.phase_gate_log
--    LEFT JOIN person — approved_by_person_id is nullable.
CREATE OR REPLACE VIEW bi.phase_gate_log AS
SELECT g.phase_gate_id, g.project_id, p.project_code,
       g.from_phase, g.to_phase, g.gate_decision,
       g.decided_at, g.gate_notes,
       g.approved_by_person_id,
       pa.display_name AS approved_by_name
FROM pmbok.phase_gate_log g
JOIN pmbok.project p USING (project_id)
LEFT JOIN doc_mgmt.person pa ON pa.person_id = g.approved_by_person_id;
