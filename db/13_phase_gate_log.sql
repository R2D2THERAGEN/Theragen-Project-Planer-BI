-- db/13_phase_gate_log.sql
-- Append-only record of lifecycle-phase handoffs (Initiating→Planning→…→Closing).
-- Each row captures who approved a phase transition, when, and the gate decision
-- (Approved / Approved with conditions / Held). Forward-only and Hold legality
-- enforced in the app layer; this table is an immutable audit log.
-- external_ref stores the SharePoint List item id for sync idempotency (the
-- db/10 convention). No DB FKs — person/project resolved in the app layer.
CREATE TABLE IF NOT EXISTS pmbok.phase_gate_log (
    phase_gate_id        UUID NOT NULL PRIMARY KEY,
    project_id           UUID NOT NULL,
    from_phase           VARCHAR NOT NULL,
    to_phase             VARCHAR NOT NULL,
    gate_decision        VARCHAR NOT NULL,
    approved_by_person_id UUID,
    decided_at           DATE,
    gate_notes           TEXT,
    external_ref         VARCHAR(64) UNIQUE
);
