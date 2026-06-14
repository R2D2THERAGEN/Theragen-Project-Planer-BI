-- db/21_cost_actual.sql
-- EVM actuals (post-2c): per-work-package, per-period actual cost so AC / CPI /
-- EAC complete the EVM family (BAC / EV / PV / SPI already derive from WBS
-- estimates + activity % complete). Authored via the daily artifact sync.
-- No DB FKs - resolved in the app, the pmbok artifact-table convention (db/10).
CREATE TABLE IF NOT EXISTS pmbok.cost_actual (
    cost_actual_id UUID NOT NULL PRIMARY KEY,
    wbs_element_id UUID NOT NULL,          -- the work package the cost is against
    period DATE NOT NULL,                  -- period the cost was incurred (month-end)
    amount NUMERIC(14,2) NOT NULL,         -- actual cost in the period
    category VARCHAR,                      -- Labor / Materials / Services / Other
    notes TEXT,
    entered_by_person_id UUID,             -- who logged it
    entered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    external_ref VARCHAR(64) UNIQUE
);

CREATE OR REPLACE VIEW bi.cost_actual AS
SELECT a.cost_actual_id,
       w.project_id,
       p.project_code,
       a.wbs_element_id,
       w.wbs_code,
       w.name             AS work_package,
       a.period,
       a.amount,
       a.category,
       a.notes,
       pe.display_name    AS entered_by_name,
       a.entered_at
FROM pmbok.cost_actual a
JOIN pmbok.wbs_element w  ON w.wbs_element_id = a.wbs_element_id
JOIN pmbok.project p      ON p.project_id     = w.project_id
LEFT JOIN doc_mgmt.person pe ON pe.person_id  = a.entered_by_person_id;
