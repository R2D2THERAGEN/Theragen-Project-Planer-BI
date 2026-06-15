-- db/24_person_directory.sql  (sub-stage D, D-T1)
-- Additive, idempotent. Applied live via inline psycopg; appended to the
-- load_postgres.py DDL file list for from-scratch parity. NEVER reseed.
--
-- Extends doc_mgmt.person into a canonical org directory (Entra roster enrichment),
-- adds a sentinel "Unassigned" department so un-curated staff satisfy the existing
-- NOT NULL person.department_id, and exposes bi.org_directory.

-- 1. Directory columns on doc_mgmt.person -------------------------------------
ALTER TABLE doc_mgmt.person ADD COLUMN IF NOT EXISTS upn VARCHAR;
ALTER TABLE doc_mgmt.person ADD COLUMN IF NOT EXISTS entra_object_id VARCHAR;
ALTER TABLE doc_mgmt.person ADD COLUMN IF NOT EXISTS job_title VARCHAR;
ALTER TABLE doc_mgmt.person ADD COLUMN IF NOT EXISTS source VARCHAR NOT NULL DEFAULT 'sharepoint';

-- entra_object_id is the stable Entra key; unique where present (Postgres treats
-- NULLs as distinct, but a partial index is explicit and keeps existing rows clean).
CREATE UNIQUE INDEX IF NOT EXISTS person_entra_object_id_uq
    ON doc_mgmt.person (entra_object_id) WHERE entra_object_id IS NOT NULL;

-- 2. Sentinel "Unassigned" department ----------------------------------------
-- doc_mgmt.person.department_id is NOT NULL; Entra-sourced staff have no curated
-- department until the PMO assigns one in the Staff Directory List (D-T4/D-T5),
-- so they land here. department_id is a fixed uuid5 (thg/department/UNAS).
INSERT INTO doc_mgmt.department (department_id, code, name, active)
VALUES ('e2cd705d-f121-52cb-a282-4efb99c9ee4a', 'UNAS', 'Unassigned', TRUE)
ON CONFLICT (code) DO NOTHING;

-- 3. bi.org_directory --------------------------------------------------------
CREATE OR REPLACE VIEW bi.org_directory AS
SELECT
    p.person_id,
    p.display_name,
    p.email,
    p.upn,
    p.job_title,
    p.active,
    p.source,
    p.employment_type,
    dep.code AS department_code,
    dep.name AS department,
    (dep.code = 'UNAS') AS department_unassigned,
    EXISTS (
        SELECT 1 FROM pmbok.report_access ra
        WHERE LOWER(ra.user_email) = LOWER(p.email) AND ra.active
    ) AS has_report_access
FROM doc_mgmt.person p
JOIN doc_mgmt.department dep ON dep.department_id = p.department_id;
