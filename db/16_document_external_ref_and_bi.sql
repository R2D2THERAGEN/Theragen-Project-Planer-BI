-- db/16_document_external_ref_and_bi.sql
-- Phase 2c-3: make controlled documents authorable + visible.
--  1. external_ref idempotency anchor on doc_mgmt.document (the SharePoint List
--     item id; UNIQUE) so the sync upserts each document without duplicates.
--  2. bi.document - a stable contract for the Power BI model over doc_mgmt.document,
--     resolving the type / department / owner / approver ids to names so the model
--     never joins doc_mgmt internals. LEFT JOIN approver (approver_person_id is
--     nullable). Additive + CREATE OR REPLACE - safe to re-run.
ALTER TABLE doc_mgmt.document ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;

CREATE OR REPLACE VIEW bi.document AS
SELECT d.document_id,
       d.doc_id,
       dt.code            AS doc_type_code,
       dt.name            AS doc_type_name,
       dep.name           AS primary_department,
       d.title,
       d.subtitle,
       d.lifecycle_phase,
       d.status,
       d.current_version,
       ow.display_name    AS owner_name,
       ap.display_name    AS approver_name,
       d.review_cycle,
       d.next_review_due,
       d.classification,
       d.storage_system,
       d.storage_path,
       d.intake_id,
       d.created_at
FROM doc_mgmt.document d
JOIN doc_mgmt.document_type dt ON dt.document_type_id = d.document_type_id
JOIN doc_mgmt.department dep   ON dep.department_id   = d.primary_department_id
JOIN doc_mgmt.person ow        ON ow.person_id        = d.owner_person_id
LEFT JOIN doc_mgmt.person ap   ON ap.person_id        = d.approver_person_id;
