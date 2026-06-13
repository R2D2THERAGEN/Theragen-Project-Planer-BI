-- db/12_project_baseline.sql
-- Immutable JSONB freeze of a project's schedule, scope, or budget at a point
-- in time. Each new baseline mints the next version (1.0, 2.0, …) and marks
-- the prior BASELINED row SUPERSEDED via superseded_by_baseline_id.
-- external_ref stores the SharePoint List item id for sync idempotency (the
-- db/10 convention). No DB FKs — person/project resolved in the app layer.
-- UNIQUE(project_id, baseline_type, version) prevents duplicate versions.
CREATE TABLE IF NOT EXISTS pmbok.project_baseline (
    baseline_id              UUID NOT NULL PRIMARY KEY,
    project_id               UUID NOT NULL,
    baseline_type            VARCHAR NOT NULL,
    version                  VARCHAR(10) NOT NULL,
    status                   VARCHAR NOT NULL DEFAULT 'BASELINED',
    change_summary           TEXT,
    change_class             VARCHAR,
    linked_cr_id             UUID,
    snapshot                 JSONB NOT NULL,
    baselined_by_person_id   UUID,
    baselined_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    superseded_by_baseline_id UUID,
    external_ref             VARCHAR(64) UNIQUE,
    CONSTRAINT uq_baseline_type_version UNIQUE (project_id, baseline_type, version)
);
