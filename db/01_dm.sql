-- ============================================================
-- doc_mgmt schema
-- Generated from Theragen DBS-001 v1.0
-- ============================================================
CREATE SCHEMA IF NOT EXISTS doc_mgmt;
-- D01  Department
-- Cross-functional department lookup.
CREATE TABLE doc_mgmt.department (
    department_id UUID NOT NULL PRIMARY KEY,
    code VARCHAR(4) NOT NULL UNIQUE,  -- CLN/REG/RND/OPS/FIN/COM/IT/HR/ENT.
    name VARCHAR(100) NOT NULL UNIQUE,  -- Display name.
    head_person_id UUID,  -- Department head.
    active BOOLEAN NOT NULL DEFAULT TRUE
);
-- D02  Person
-- Workforce member or external contributor.
CREATE TABLE doc_mgmt.person (
    person_id UUID NOT NULL PRIMARY KEY,
    employee_number VARCHAR(20) UNIQUE,  -- HRIS identifier.
    email VARCHAR(254) NOT NULL UNIQUE,  -- Primary email.
    display_name VARCHAR(150) NOT NULL,  -- Full name.
    department_id UUID NOT NULL,  -- Home department.
    role_id UUID,  -- Primary role.
    manager_person_id UUID,  -- Reporting manager (self-ref).
    employment_type VARCHAR NOT NULL DEFAULT 'Employee',  -- employment_type
    active BOOLEAN NOT NULL DEFAULT TRUE,
    start_date DATE NOT NULL,  -- Start date.
    end_date DATE  -- End date (if any).
);
-- D03  Role
-- Job role catalog.
CREATE TABLE doc_mgmt.role (
    role_id UUID NOT NULL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,  -- Role name.
    department_id UUID,  -- Owning department, if specific.
    controlled_work BOOLEAN NOT NULL DEFAULT TRUE,
    description TEXT  -- Role description.
);
-- D04  Compliance Frame
-- Regulatory or methodological frame.
CREATE TABLE doc_mgmt.compliance_frame (
    frame_id UUID NOT NULL PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,  -- Short code.
    name VARCHAR(100) NOT NULL UNIQUE,  -- Display name.
    authority VARCHAR(100) NOT NULL,  -- Issuing body.
    applies_to TEXT NOT NULL,  -- When applicable.
    reference_url VARCHAR(500)  -- Authoritative source URL.
);
-- D05  Document Type
-- Controlled document type catalog (CHR, SOP, etc.).
CREATE TABLE doc_mgmt.document_type (
    document_type_id UUID NOT NULL PRIMARY KEY,
    code VARCHAR(4) NOT NULL UNIQUE,  -- 3-letter type code.
    name VARCHAR(100) NOT NULL,  -- Plain name.
    lifecycle_phase VARCHAR NOT NULL,  -- lifecycle_phase
    default_review_cycle VARCHAR NOT NULL DEFAULT 'Annual',  -- review_cycle
    requires_approval BOOLEAN NOT NULL DEFAULT TRUE
);
-- D06  Controlled Template
-- Versioned blank template that documents are created from.
CREATE TABLE doc_mgmt.controlled_template (
    template_id UUID NOT NULL PRIMARY KEY,
    template_code VARCHAR(30) NOT NULL UNIQUE,  -- Template Doc ID.
    document_type_id UUID NOT NULL,  -- Which type.
    title VARCHAR(200) NOT NULL,  -- Template title.
    version VARCHAR(10) NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'BASELINE',  -- doc_status
    storage_path VARCHAR(500) NOT NULL,  -- SharePoint or repo path.
    owner_person_id UUID NOT NULL,  -- Template owner.
    published_at TIMESTAMPTZ NOT NULL  -- Publication timestamp.
);
-- D07  Document
-- Controlled document record. The spine of the DM schema.
CREATE TABLE doc_mgmt.document (
    document_id UUID NOT NULL PRIMARY KEY,
    doc_id VARCHAR(30) NOT NULL UNIQUE,  -- Theragen Doc ID, e.g. THG-OPS-CHR-014.
    document_type_id UUID NOT NULL,  -- Type.
    primary_department_id UUID NOT NULL,  -- Owning department.
    title VARCHAR(200) NOT NULL,  -- Document title.
    subtitle VARCHAR(500),  -- One-line subtitle.
    lifecycle_phase VARCHAR NOT NULL,  -- lifecycle_phase
    status VARCHAR NOT NULL DEFAULT 'DRAFT',  -- doc_status
    current_version VARCHAR(10) NOT NULL,
    owner_person_id UUID NOT NULL,  -- Document Owner.
    approver_person_id UUID,  -- Designated Approver.
    review_cycle VARCHAR NOT NULL DEFAULT 'Annual',  -- review_cycle
    next_review_due DATE,  -- Next periodic review due date.
    intake_id VARCHAR(16),  -- Originating intake.
    classification VARCHAR NOT NULL DEFAULT 'Confidential – Internal',  -- classification
    storage_system VARCHAR NOT NULL DEFAULT 'PMO SharePoint',  -- storage_system
    storage_path VARCHAR(500) NOT NULL,  -- File path or URL.
    retired_at TIMESTAMPTZ,  -- If retired, when.
    superseded_by_document_id UUID,  -- Successor doc if any.
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- D08  Document Version
-- Immutable version history for a Document.
CREATE TABLE doc_mgmt.document_version (
    version_id UUID NOT NULL PRIMARY KEY,
    document_id UUID NOT NULL,  -- Parent document.
    version VARCHAR(10) NOT NULL,  -- Version string.
    status VARCHAR NOT NULL DEFAULT 'DRAFT',  -- doc_status
    change_summary TEXT NOT NULL,  -- What changed.
    change_class VARCHAR,  -- cr_class
    linked_cr_id UUID,  -- Linked CR.
    author_person_id UUID NOT NULL,  -- Author.
    effective_date DATE,  -- Effective on.
    storage_path VARCHAR(500) NOT NULL,  -- Versioned file path.
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- D09  Document Review
-- Review event prior to baseline or amendment.
CREATE TABLE doc_mgmt.document_review (
    review_id UUID NOT NULL PRIMARY KEY,
    version_id UUID NOT NULL,  -- Version under review.
    reviewer_person_id UUID NOT NULL,  -- Reviewer.
    review_type VARCHAR NOT NULL DEFAULT 'Technical',  -- review_type
    disposition VARCHAR NOT NULL,  -- review_disposition
    comments TEXT,  -- Comments / dispositions.
    reviewed_at TIMESTAMPTZ NOT NULL  -- Review timestamp.
);
-- D10  Document Approval
-- 21 CFR Part 11 §11.50 signed approval.
CREATE TABLE doc_mgmt.document_approval (
    approval_id UUID NOT NULL PRIMARY KEY,
    version_id UUID NOT NULL,  -- Version being approved.
    approver_person_id UUID NOT NULL,  -- Approver.
    signature_meaning VARCHAR NOT NULL DEFAULT 'Approval',  -- signature_meaning
    signed_at TIMESTAMPTZ NOT NULL,  -- Sign timestamp.
    esig_hash VARCHAR(128) NOT NULL,  -- Signature hash.
    ip_address INET,  -- Client IP at signing.
    reason TEXT  -- Reason / context.
);
-- D11  Document Retirement
-- Retirement event for a baselined document.
CREATE TABLE doc_mgmt.document_retirement (
    retirement_id UUID NOT NULL PRIMARY KEY,
    document_id UUID NOT NULL,  -- Document retired.
    retired_by_person_id UUID NOT NULL,  -- Approver of retirement.
    reason TEXT NOT NULL,  -- Why retired.
    superseded_by_document_id UUID,  -- Successor.
    archive_path VARCHAR(500) NOT NULL,  -- Archive location.
    retired_at TIMESTAMPTZ NOT NULL  -- Retirement timestamp.
);
-- D12  Intake Submission
-- Submitted Integrated Intake Form.
CREATE TABLE doc_mgmt.intake_submission (
    intake_submission_id UUID NOT NULL PRIMARY KEY,
    intake_id VARCHAR(16) NOT NULL UNIQUE,  -- INT-YYYY-NNNN.
    submitted_at TIMESTAMPTZ NOT NULL,  -- Submission timestamp.
    requester_person_id UUID NOT NULL,  -- Requester.
    requesting_department_id UUID NOT NULL,  -- Requesting department.
    request_title VARCHAR(200) NOT NULL,  -- Request title.
    request_type VARCHAR NOT NULL,  -- request_type
    business_problem TEXT NOT NULL,  -- 2-4 sentences.
    desired_outcome TEXT NOT NULL,  -- Success definition.
    strategic_linkage TEXT,  -- Linked strategic objective.
    requested_by_date DATE,  -- Need-by date.
    scope_in TEXT,  -- Scope sketch — in.
    scope_out TEXT,  -- Scope sketch — out.
    phi_flag BOOLEAN NOT NULL DEFAULT FALSE,
    cfr11_flag BOOLEAN NOT NULL DEFAULT FALSE,
    clinical_flag BOOLEAN NOT NULL DEFAULT FALSE,
    vendor_flag BOOLEAN NOT NULL DEFAULT FALSE,
    data_sharing_flag BOOLEAN NOT NULL DEFAULT FALSE,
    effort VARCHAR NOT NULL,  -- effort_bucket
    budget_envelope VARCHAR NOT NULL DEFAULT 'Unknown',  -- budget_envelope
    funding_source VARCHAR,  -- funding_source
    status VARCHAR NOT NULL DEFAULT 'Submitted'  -- intake_status
);
-- D13  Intake Compliance Pre-screen
-- Per-frame pre-screen attestation.
CREATE TABLE doc_mgmt.intake_compliance_prescreen (
    prescreen_id UUID NOT NULL PRIMARY KEY,
    intake_id VARCHAR(16) NOT NULL,  -- Parent intake.
    frame_id UUID NOT NULL,  -- Frame screened.
    reviewer_person_id UUID NOT NULL,  -- Pre-screen reviewer.
    decision VARCHAR NOT NULL,  -- prescreen_decision
    rationale TEXT NOT NULL,  -- Rationale / conditions.
    reviewed_at TIMESTAMPTZ NOT NULL  -- Timestamp.
);
-- D14  Intake Decision
-- Triage decision and routing for an intake.
CREATE TABLE doc_mgmt.intake_decision (
    decision_id UUID NOT NULL PRIMARY KEY,
    intake_id VARCHAR(16) NOT NULL UNIQUE,  -- Parent intake.
    decided_by_person_id UUID NOT NULL,  -- PMO Director or delegate.
    decided_at TIMESTAMPTZ NOT NULL,  -- Timestamp.
    decision VARCHAR NOT NULL,  -- intake_decision
    primary_department_id UUID NOT NULL,  -- Assigned primary department.
    secondary_departments TEXT,  -- JSON array of department codes.
    linked_charter_doc_id VARCHAR(30),  -- Charter once issued.
    linked_project_id UUID,  -- Project once kicked off.
    notes TEXT  -- Triage notes.
);
-- D15  RACI Assignment
-- Per-document, per-department R/A/C/I role.
CREATE TABLE doc_mgmt.raci_assignment (
    raci_id UUID NOT NULL PRIMARY KEY,
    document_id UUID NOT NULL,  -- Document.
    department_id UUID NOT NULL,  -- Department.
    role VARCHAR NOT NULL,  -- raci_role
    touchpoint VARCHAR(300),  -- What the dept does on this doc.
    valid_from DATE NOT NULL,  -- Effective from.
    valid_to DATE  -- Effective to (open ended).
);
-- D16  Document × Compliance Mapping
-- Which frames govern which doc; with evidence link.
CREATE TABLE doc_mgmt.doc_compliance_mapping (
    mapping_id UUID NOT NULL PRIMARY KEY,
    document_id UUID NOT NULL,  -- Document.
    frame_id UUID NOT NULL,  -- Frame.
    applies_to_sections TEXT,  -- Which sections of the doc.
    evidence_reference TEXT  -- Audit evidence pointer.
);
-- D17  Change Request (Governance)
-- CR against a controlled document. Class A/B/C per SOP-003.
CREATE TABLE doc_mgmt.change_request_gov (
    cr_gov_id UUID NOT NULL PRIMARY KEY,
    cr_code VARCHAR(8) NOT NULL UNIQUE,  -- CHG-NNN.
    document_id UUID NOT NULL,  -- Target controlled document.
    intake_id VARCHAR(16),  -- Linked intake if applicable.
    requested_at DATE NOT NULL,  -- Submission date.
    requested_by_person_id UUID NOT NULL,  -- Requester.
    cr_class VARCHAR NOT NULL,  -- cr_class
    description TEXT NOT NULL,  -- Proposed change.
    reason TEXT NOT NULL,  -- Driver.
    decision VARCHAR NOT NULL DEFAULT 'Pending',  -- cr_decision
    decided_by_person_id UUID,  -- Approver.
    decided_at DATE,  -- Decision date.
    implementation_verified BOOLEAN DEFAULT FALSE,
    status VARCHAR NOT NULL DEFAULT 'Open'  -- cr_status
);
-- D18  Change Impact Assessment (Gov)
-- Per-department impact statement on a governance CR.
CREATE TABLE doc_mgmt.change_assessment_gov (
    gov_impact_id UUID NOT NULL PRIMARY KEY,
    cr_gov_id UUID NOT NULL,  -- Parent CR.
    department_id UUID NOT NULL,  -- Assessor's department.
    impact_summary TEXT NOT NULL,  -- Impact statement.
    compliance_impact TEXT,  -- Compliance / regulatory impact.
    submitted_at DATE NOT NULL  -- Submission date.
);
-- D19  Training Curriculum
-- Set of documents required for a given role.
CREATE TABLE doc_mgmt.training_curriculum (
    curriculum_id UUID NOT NULL PRIMARY KEY,
    code VARCHAR(30) NOT NULL UNIQUE,  -- Curriculum code.
    name VARCHAR(100) NOT NULL,  -- Curriculum name.
    role_id UUID,  -- Role this curriculum targets.
    department_id UUID,  -- Owning department.
    active BOOLEAN NOT NULL DEFAULT TRUE
);
-- D20  Curriculum Item
-- Document required by a curriculum.
CREATE TABLE doc_mgmt.curriculum_item (
    curriculum_item_id UUID NOT NULL PRIMARY KEY,
    curriculum_id UUID NOT NULL,  -- Parent curriculum.
    document_id UUID NOT NULL,  -- Required doc.
    required BOOLEAN NOT NULL DEFAULT TRUE,
    sequence SMALLINT NOT NULL DEFAULT 1
);
-- D21  Training Assignment
-- Curriculum or single doc assigned to a person.
CREATE TABLE doc_mgmt.training_assignment (
    assignment_id UUID NOT NULL PRIMARY KEY,
    person_id UUID NOT NULL,  -- Trainee.
    document_id UUID NOT NULL,  -- Specific doc.
    curriculum_id UUID,  -- Curriculum that triggered the assignment.
    assigned_at DATE NOT NULL,  -- Assignment date.
    target_date DATE NOT NULL,  -- Target completion.
    status VARCHAR NOT NULL DEFAULT 'Assigned',  -- training_status
    manager_person_id UUID NOT NULL  -- Assigning manager.
);
-- D22  Comprehension Check
-- Quiz attempt result tied to an assignment.
CREATE TABLE doc_mgmt.comprehension_check (
    check_id UUID NOT NULL PRIMARY KEY,
    assignment_id UUID NOT NULL,  -- Parent assignment.
    attempt_number SMALLINT NOT NULL DEFAULT 1,
    score_pct NUMERIC(5,2) NOT NULL,
    passed BOOLEAN NOT NULL DEFAULT FALSE,
    taken_at TIMESTAMPTZ NOT NULL  -- Quiz timestamp.
);
-- D23  Training Attestation
-- Signed attestation under 21 CFR §11.50.
CREATE TABLE doc_mgmt.training_attestation (
    attestation_id UUID NOT NULL PRIMARY KEY,
    assignment_id UUID NOT NULL,  -- Parent assignment.
    person_id UUID NOT NULL,  -- Trainee.
    document_id UUID NOT NULL,  -- Doc attested to.
    version VARCHAR(10) NOT NULL,  -- Doc version at attestation.
    attestation_meaning VARCHAR NOT NULL DEFAULT 'Training Attestation',  -- signature_meaning
    attested_at TIMESTAMPTZ NOT NULL,  -- Signed timestamp.
    esig_hash VARCHAR(128) NOT NULL,  -- Signature hash.
    refresher_due DATE  -- Next refresher date.
);
-- D24  Records Retention Policy
-- Retention rules per record class.
CREATE TABLE doc_mgmt.records_retention_policy (
    policy_id UUID NOT NULL PRIMARY KEY,
    record_class VARCHAR NOT NULL UNIQUE,  -- Record class.
    system_of_record VARCHAR NOT NULL,  -- storage_system
    retention_years SMALLINT NOT NULL,
    retention_basis VARCHAR NOT NULL,  -- retention_basis
    disposition_default VARCHAR NOT NULL DEFAULT 'Archive',  -- disposition
    legal_basis VARCHAR(200)  -- Citation.
);
-- D25  Records Disposition
-- Disposition event for a record reaching end of retention.
CREATE TABLE doc_mgmt.records_disposition (
    disposition_id UUID NOT NULL PRIMARY KEY,
    document_id UUID,  -- Linked document.
    record_class VARCHAR NOT NULL,  -- record_class
    disposition VARCHAR NOT NULL,  -- disposition
    disposed_by_person_id UUID NOT NULL,  -- Records Steward.
    disposed_at DATE NOT NULL,  -- Disposition date.
    method VARCHAR(200),  -- Method (shred / archive / transfer).
    approved_by_person_id UUID NOT NULL,  -- Approver.
    notes TEXT  -- Notes.
);
-- D26  Audit Evidence Pack
-- Curated record set assembled for an audit.
CREATE TABLE doc_mgmt.audit_evidence_pack (
    pack_id UUID NOT NULL PRIMARY KEY,
    pack_code VARCHAR(30) NOT NULL UNIQUE,  -- Pack code.
    audit_name VARCHAR(200) NOT NULL,  -- Audit description.
    audit_scope TEXT NOT NULL,  -- Scope of evidence.
    frame_id UUID NOT NULL,  -- Frame being audited.
    prepared_by_person_id UUID NOT NULL,  -- Pack owner.
    prepared_at TIMESTAMPTZ NOT NULL,  -- Pack assembly time.
    audit_start DATE NOT NULL,  -- Audit start.
    audit_end DATE,  -- Audit end.
    outcome VARCHAR,  -- audit_outcome
    retain_until DATE NOT NULL  -- Retention end (audit + 7 yrs).
);
-- D27  Audit Evidence Item
-- Individual record included in an evidence pack.
CREATE TABLE doc_mgmt.audit_evidence_item (
    evidence_item_id UUID NOT NULL PRIMARY KEY,
    pack_id UUID NOT NULL,  -- Parent pack.
    document_id UUID,  -- Linked document.
    attestation_id UUID,  -- Linked attestation.
    disposition_id UUID,  -- Linked disposition.
    description TEXT NOT NULL,  -- What this item demonstrates.
    added_by_person_id UUID NOT NULL,  -- Person who added.
    added_at TIMESTAMPTZ NOT NULL  -- Add timestamp.
);
-- D28  Deviation
-- Documented deviation from an SOP.
CREATE TABLE doc_mgmt.deviation (
    deviation_id UUID NOT NULL PRIMARY KEY,
    sop_document_id UUID NOT NULL,  -- SOP deviated from.
    reported_by_person_id UUID NOT NULL,  -- Reporter.
    reported_at TIMESTAMPTZ NOT NULL,  -- Timestamp.
    severity VARCHAR NOT NULL,  -- severity
    description TEXT NOT NULL,  -- What happened.
    root_cause TEXT,  -- Root cause if known.
    capa_id UUID,  -- Linked CAPA if opened.
    status VARCHAR NOT NULL DEFAULT 'Open'  -- deviation_status
);
-- D29  CAPA Record
-- Corrective and Preventive Action.
CREATE TABLE doc_mgmt.capa (
    capa_id UUID NOT NULL PRIMARY KEY,
    code VARCHAR(16) NOT NULL UNIQUE,  -- CAPA-NNN.
    trigger VARCHAR NOT NULL,  -- capa_trigger
    opened_at DATE NOT NULL,  -- Open date.
    opened_by_person_id UUID NOT NULL,  -- Opener.
    owner_person_id UUID NOT NULL,  -- CAPA owner.
    root_cause_due DATE NOT NULL,  -- RCA due.
    root_cause TEXT,  -- Root cause analysis.
    corrective_action TEXT,  -- Corrective action.
    preventive_action TEXT,  -- Preventive action.
    effectiveness_review_due DATE,  -- Effectiveness check due.
    status VARCHAR NOT NULL DEFAULT 'Open',  -- capa_status
    closed_at DATE  -- Closure date.
);
-- D30  Access Grant
-- Role-based access assignment to a document.
CREATE TABLE doc_mgmt.access_grant (
    grant_id UUID NOT NULL PRIMARY KEY,
    document_id UUID NOT NULL,  -- Document.
    principal_type VARCHAR NOT NULL,  -- principal_type
    principal_id UUID NOT NULL,  -- ID of person/role/department.
    permission VARCHAR NOT NULL DEFAULT 'Read',  -- permission
    granted_by_person_id UUID NOT NULL,  -- Granter.
    granted_at TIMESTAMPTZ NOT NULL,  -- Grant timestamp.
    revoked_at TIMESTAMPTZ  -- Revocation timestamp.
);
-- D31  Audit Trail Entry
-- Append-only audit log entry (21 CFR §11.10(e)).
CREATE TABLE doc_mgmt.audit_trail_entry (
    trail_id BIGSERIAL NOT NULL PRIMARY KEY,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor_person_id UUID,  -- Acting person.
    action VARCHAR NOT NULL,  -- audit_action
    entity_type VARCHAR(50) NOT NULL,  -- Entity touched.
    entity_id UUID NOT NULL,  -- Entity ID.
    before_state JSONB,  -- Pre-image.
    after_state JSONB,  -- Post-image.
    ip_address INET,  -- Client IP.
    reason TEXT  -- Reason supplied.
);
