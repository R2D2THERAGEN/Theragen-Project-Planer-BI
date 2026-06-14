-- db/22_report_access.sql
-- Data-driven Row-Level Security (compliance hardening): authored access grants
-- that the "Scoped Viewer" model role reads to filter Project (and thus every
-- fact, via the single-direction relationships) by USERPRINCIPALNAME().
-- Default-deny - a user with no active grant sees nothing. A grant is
-- (user_email, scope_type, scope_value): Project + a project_code, Department +
-- a department name, or All (blank value). A user gets the UNION of their grants.
-- App-resolved (no DB FKs, the pmbok artifact-table convention).
CREATE TABLE IF NOT EXISTS pmbok.report_access (
    access_id UUID NOT NULL PRIMARY KEY,
    user_email VARCHAR(254) NOT NULL,      -- grantee UPN/email (matches person.email)
    scope_type VARCHAR NOT NULL,           -- Project / Department / All
    scope_value VARCHAR,                   -- project_code or department name; NULL for All
    granted_by_person_id UUID,             -- who authored the grant
    active BOOLEAN NOT NULL DEFAULT TRUE,  -- soft-disable a grant without deleting it
    granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    external_ref VARCHAR(64) UNIQUE
);

CREATE OR REPLACE VIEW bi.report_access AS
SELECT a.access_id,
       a.user_email,
       a.scope_type,
       a.scope_value,
       a.active,
       pe.display_name AS granted_by_name,
       a.granted_at
FROM pmbok.report_access a
LEFT JOIN doc_mgmt.person pe ON pe.person_id = a.granted_by_person_id;
