-- db/25_person_directory_org.sql  (sub-stage E, E-T2)
-- Curated org structure on the directory: office location + manager. Entra has
-- neither for Theragen staff (manager 1%, location 9%), so the PMO maintains them
-- via the Staff Directory List (read back like Department). Additive, idempotent;
-- applied via inline psycopg; appended to the load_postgres.py DDL list.
-- `doc_mgmt.person.manager_person_id` already exists (nullable, app-resolved).

ALTER TABLE doc_mgmt.person ADD COLUMN IF NOT EXISTS office_location VARCHAR;

-- Widen bi.org_directory with office_location + the manager's name/email
-- (self-join person on manager_person_id; LEFT so no-manager rows survive).
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
    ) AS has_report_access,
    -- new columns appended at the end (CREATE OR REPLACE VIEW only allows appends)
    p.office_location,
    mgr.display_name AS manager_name,
    mgr.email AS manager_email
FROM doc_mgmt.person p
JOIN doc_mgmt.department dep ON dep.department_id = p.department_id
LEFT JOIN doc_mgmt.person mgr ON mgr.person_id = p.manager_person_id;
