-- db/23_platform_change.sql
-- Round 2 dogfood: the platform change register (CHANGELOG as live, governed data).
-- Additive; applied live via inline psycopg (never load_postgres.py). Project-less,
-- app-resolved persons (the db/10 convention -- no DB FKs on pmbok artifact tables).

CREATE TABLE IF NOT EXISTS pmbok.platform_change (
    change_id              UUID PRIMARY KEY,
    category               VARCHAR(40)  NOT NULL,   -- one of the 6 change-control-process.md categories
    summary                TEXT         NOT NULL,
    version                VARCHAR(20),             -- platform version this change targets (e.g. 2.7)
    status                 VARCHAR(20)  NOT NULL DEFAULT 'Proposed',  -- Proposed / Approved / Deployed
    requested_by_person_id UUID,
    approved_by_person_id  UUID,
    git_sha                VARCHAR(40),
    changed_at             DATE,
    external_ref           VARCHAR(64) UNIQUE
);

CREATE OR REPLACE VIEW bi.platform_change AS
SELECT pc.change_id,
       pc.category,
       pc.summary,
       pc.version,
       pc.status,
       pc.requested_by_person_id,
       rb.display_name AS requested_by_name,
       pc.approved_by_person_id,
       ab.display_name AS approved_by_name,
       pc.git_sha,
       pc.changed_at
FROM pmbok.platform_change pc
LEFT JOIN doc_mgmt.person rb ON rb.person_id = pc.requested_by_person_id
LEFT JOIN doc_mgmt.person ab ON ab.person_id = pc.approved_by_person_id;
