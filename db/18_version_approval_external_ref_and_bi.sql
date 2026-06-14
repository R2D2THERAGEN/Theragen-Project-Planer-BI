-- db/18_version_approval_external_ref_and_bi.sql
-- Phase 2c-5: document version history + per-version sign-off ATTESTATIONS.
--  1. external_ref idempotency anchors on document_version + document_approval.
--  2. bi.document_version - version metadata, author resolved to a name.
--  3. bi.document_approval - the attestation, version+document+approver resolved,
--     with a literal esig_kind = 'Attestation (non-§11)' so no downstream surface
--     can mistake the server-computed hash for a true 21 CFR Part 11 signature.
-- Additive + CREATE OR REPLACE - safe to re-run.
ALTER TABLE doc_mgmt.document_version  ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;
ALTER TABLE doc_mgmt.document_approval ADD COLUMN IF NOT EXISTS external_ref VARCHAR(64) UNIQUE;

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
       v.created_at
FROM doc_mgmt.document_version v
JOIN doc_mgmt.document d  ON d.document_id = v.document_id
JOIN doc_mgmt.person au  ON au.person_id  = v.author_person_id;

CREATE OR REPLACE VIEW bi.document_approval AS
SELECT a.approval_id,
       a.version_id,
       d.doc_id,
       d.title            AS doc_title,
       v.version,
       ap.display_name    AS approver_name,
       a.signature_meaning,
       a.signed_at,
       a.esig_hash,
       'Attestation (non-§11)'::text AS esig_kind,
       a.reason
FROM doc_mgmt.document_approval a
JOIN doc_mgmt.document_version v ON v.version_id  = a.version_id
JOIN doc_mgmt.document d         ON d.document_id = v.document_id
JOIN doc_mgmt.person ap          ON ap.person_id  = a.approver_person_id;
