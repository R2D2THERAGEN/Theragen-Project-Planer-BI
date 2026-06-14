-- db/17_raci_external_ref_and_bi.sql
-- Phase 2c-4: per-document R/A/C/I (RACI) assignment authoring.
--  1. external_ref idempotency anchor on doc_mgmt.raci_assignment (the SharePoint
--     List item id; UNIQUE) so the sync upserts each assignment without duplicates.
--  2. bi.raci_assignment - resolves the parent document + assignee department to
--     names and expands the single-char role to a friendly role_name. Additive +
--     CREATE OR REPLACE - safe to re-run.
ALTER TABLE doc_mgmt.raci_assignment ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;

CREATE OR REPLACE VIEW bi.raci_assignment AS
SELECT r.raci_id,
       r.document_id,
       d.doc_id,
       d.title            AS doc_title,
       r.department_id,
       dep.name           AS department,
       r.role,
       CASE r.role WHEN 'R' THEN 'Responsible'
                   WHEN 'A' THEN 'Accountable'
                   WHEN 'C' THEN 'Consulted'
                   WHEN 'I' THEN 'Informed'
                   ELSE r.role END AS role_name,
       r.touchpoint,
       r.valid_from,
       r.valid_to
FROM doc_mgmt.raci_assignment r
JOIN doc_mgmt.document d     ON d.document_id   = r.document_id
JOIN doc_mgmt.department dep ON dep.department_id = r.department_id;
