-- db/19_govcr_external_ref_and_bi.sql
-- Phase 2c-6 (finale): governance change requests + per-department assessments.
--  1. external_ref idempotency anchors on change_request_gov + change_assessment_gov.
--  2. bi.change_request_gov  - document-scoped CR, requester/decider resolved to names.
--  3. bi.change_assessment_gov - per-department impact statement on a governance CR.
--  4. widen bi.document_version with linked_cr_id + linked_cr_code, closing the
--     LinkedCR loop deferred from 2c-5 (a version can now cite the governance CR
--     that drove it). LEFT JOIN so unlinked versions are unaffected.
-- Additive + CREATE OR REPLACE - safe to re-run.
ALTER TABLE doc_mgmt.change_request_gov    ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;
ALTER TABLE doc_mgmt.change_assessment_gov ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;

CREATE OR REPLACE VIEW bi.change_request_gov AS
SELECT c.cr_gov_id,
       c.cr_code,
       c.document_id,
       d.doc_id,
       d.title              AS doc_title,
       c.intake_id,
       c.requested_at,
       rq.display_name      AS requested_by_name,
       c.cr_class,
       c.description,
       c.reason,
       c.decision,
       dc.display_name      AS decided_by_name,
       c.decided_at,
       c.implementation_verified,
       c.status
FROM doc_mgmt.change_request_gov c
JOIN doc_mgmt.document d   ON d.document_id  = c.document_id
JOIN doc_mgmt.person rq    ON rq.person_id   = c.requested_by_person_id
LEFT JOIN doc_mgmt.person dc ON dc.person_id = c.decided_by_person_id;

CREATE OR REPLACE VIEW bi.change_assessment_gov AS
SELECT a.gov_impact_id,
       a.cr_gov_id,
       c.cr_code,
       d.doc_id,
       d.title          AS doc_title,
       dep.name         AS department,
       a.impact_summary,
       a.compliance_impact,
       a.submitted_at
FROM doc_mgmt.change_assessment_gov a
JOIN doc_mgmt.change_request_gov c ON c.cr_gov_id    = a.cr_gov_id
JOIN doc_mgmt.document d           ON d.document_id  = c.document_id
JOIN doc_mgmt.department dep       ON dep.department_id = a.department_id;

-- Widen bi.document_version: surface the linked governance CR (2c-6 loop closure).
CREATE OR REPLACE VIEW bi.document_version AS
SELECT v.version_id,
       v.document_id,
       d.doc_id,
       d.title            AS doc_title,
       v.version,
       v.status,
       v.change_summary,
       v.change_class,
       au.display_name    AS author_name,
       v.effective_date,
       v.storage_path,
       v.created_at,
       v.linked_cr_id,
       lcr.cr_code        AS linked_cr_code
FROM doc_mgmt.document_version v
JOIN doc_mgmt.document d  ON d.document_id = v.document_id
JOIN doc_mgmt.person au  ON au.person_id  = v.author_person_id
LEFT JOIN doc_mgmt.change_request_gov lcr ON lcr.cr_gov_id = v.linked_cr_id;
