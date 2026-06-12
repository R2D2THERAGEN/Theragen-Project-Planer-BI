-- ============================================================
-- pmbok schema
-- Generated from Theragen DBS-001 v1.0
-- ============================================================
CREATE SCHEMA IF NOT EXISTS pmbok;
-- P01  Project
-- Top-level project record. The container all other PMBOK rows belong to.
CREATE TABLE pmbok.project (
    project_id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,  -- Surrogate primary key.
    project_code VARCHAR(32) NOT NULL UNIQUE,  -- Human-readable project code (e.g. THG-CLN-001).
    intake_id VARCHAR(16) NOT NULL,  -- Originating Intake ID. Propagates traceability from DM schema.
    name VARCHAR(200) NOT NULL,  -- Project name.
    description TEXT,  -- One-paragraph project description.
    sponsor_person_id UUID NOT NULL,  -- Project Sponsor.
    project_manager_id UUID NOT NULL,  -- Assigned Project Manager.
    primary_department VARCHAR NOT NULL,  -- Owning department.
    approach VARCHAR NOT NULL DEFAULT 'predictive',  -- Delivery approach.
    lifecycle_phase VARCHAR NOT NULL DEFAULT 'Initiating',  -- Current PMI process group.
    status VARCHAR NOT NULL DEFAULT 'Active',  -- Project lifecycle state.
    planned_start DATE,  -- Baseline start date.
    planned_finish DATE,  -- Baseline finish date.
    actual_start DATE,  -- Actual start.
    actual_finish DATE,  -- Actual finish.
    budget_total NUMERIC(12,2),  -- Approved budget total (USD).
    strategic_objective_ref VARCHAR(100),  -- Linked strategic objective.
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),  -- Row created timestamp.
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()  -- Row updated timestamp.
);
-- P02  Project Charter
-- Authorization document. One per Project.
CREATE TABLE pmbok.project_charter (
    charter_id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,  -- Surrogate PK.
    project_id UUID NOT NULL,  -- Parent project.
    doc_id VARCHAR(20) NOT NULL UNIQUE,  -- DM-side document identifier.
    business_case TEXT NOT NULL,  -- Why now; expected benefit; strategic linkage.
    high_level_in_scope TEXT NOT NULL,  -- Bulleted in-scope summary.
    high_level_out_scope TEXT,  -- Bulleted out-of-scope summary.
    budget_estimate_low NUMERIC(12,2),  -- Order-of-magnitude low.
    budget_estimate_high NUMERIC(12,2),  -- Order-of-magnitude high.
    pm_authority_text TEXT NOT NULL,  -- Authority granted to the PM.
    approved_by_person_id UUID,  -- Sponsor who approved.
    approved_at TIMESTAMPTZ,  -- Approval timestamp.
    status VARCHAR NOT NULL DEFAULT 'DRAFT',  -- Doc lifecycle status.
    version VARCHAR(10) NOT NULL DEFAULT 0.1  -- Charter version.
);
-- P03  Stakeholder Register Entry
-- Person or group with interest or influence in the project.
CREATE TABLE pmbok.stakeholder (
    stakeholder_id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,  -- Surrogate PK.
    project_id UUID NOT NULL,  -- Parent project.
    stk_code VARCHAR(8) NOT NULL,  -- S-NNN persistent ID.
    person_id UUID,  -- Linked person (optional if group).
    group_name VARCHAR(100),  -- Group name when not a person.
    role VARCHAR(100) NOT NULL,  -- Role in the project context.
    department VARCHAR NOT NULL,  -- Department.
    engagement VARCHAR NOT NULL DEFAULT 'C',  -- RACI engagement on the project.
    interest VARCHAR NOT NULL DEFAULT 'Medium',  -- Interest level.
    influence VARCHAR NOT NULL DEFAULT 'Medium',  -- Influence level.
    expectations TEXT,  -- Stakeholder expectations.
    communication_preference VARCHAR,  -- Preferred channel.
    engagement_strategy TEXT  -- Engagement plan summary.
);
-- P04  Project Scope Statement
-- Approved scope document. One per Project.
CREATE TABLE pmbok.scope_statement (
    scope_id UUID NOT NULL PRIMARY KEY,
    project_id UUID NOT NULL,  -- Parent project.
    doc_id VARCHAR(20) NOT NULL UNIQUE,  -- DM-side doc ID.
    product_description TEXT NOT NULL,  -- Description of deliverable / outcome.
    status VARCHAR NOT NULL DEFAULT 'DRAFT',  -- Doc lifecycle status.
    version VARCHAR(10) NOT NULL DEFAULT 0.1  -- Version.
);
-- P05  Scope Inclusion
-- Item explicitly in scope.
CREATE TABLE pmbok.scope_inclusion (
    inclusion_id UUID NOT NULL PRIMARY KEY,
    scope_id UUID NOT NULL,  -- Parent scope doc.
    sequence SMALLINT NOT NULL,  -- Display order.
    item TEXT NOT NULL,  -- Inclusion text.
    owning_department VARCHAR  -- Owning department.
);
-- P06  Scope Exclusion
-- Item explicitly out of scope.
CREATE TABLE pmbok.scope_exclusion (
    exclusion_id UUID NOT NULL PRIMARY KEY,
    scope_id UUID NOT NULL,  -- Parent scope doc.
    sequence SMALLINT NOT NULL,  -- Display order.
    item TEXT NOT NULL,  -- Exclusion text.
    reason TEXT  -- Reason it's out of scope.
);
-- P07  Acceptance Criterion
-- Verification condition the deliverable must meet.
CREATE TABLE pmbok.acceptance_criterion (
    criterion_id UUID NOT NULL PRIMARY KEY,
    scope_id UUID NOT NULL,  -- Parent scope doc.
    sequence SMALLINT NOT NULL,  -- Display order.
    criterion TEXT NOT NULL,  -- Criterion statement.
    verification_method VARCHAR NOT NULL DEFAULT 'Test',  -- Method.
    owner_role VARCHAR(100) NOT NULL,  -- Role accountable for verification.
    status VARCHAR NOT NULL DEFAULT 'Open'  -- Verification state.
);
-- P08  WBS Element
-- Hierarchical work breakdown node. Self-referencing parent.
CREATE TABLE pmbok.wbs_element (
    wbs_element_id UUID NOT NULL PRIMARY KEY,
    project_id UUID NOT NULL,  -- Parent project.
    wbs_code VARCHAR(20) NOT NULL,  -- Dotted ID like 1.3.2. Unique within project.
    parent_wbs_element_id UUID,  -- Self-reference for hierarchy.
    level SMALLINT NOT NULL,  -- Depth in tree (1 = top).
    name VARCHAR(200) NOT NULL,  -- Deliverable / work package name.
    owning_department VARCHAR NOT NULL,  -- Department owning this WP.
    owner_role VARCHAR(100) NOT NULL,  -- Owning role.
    estimated_effort_hrs NUMERIC(9,2),  -- Effort estimate.
    estimated_cost NUMERIC(12,2),  -- Cost estimate.
    accepted_by_person_id UUID  -- Who accepted the deliverable.
);
-- P09  WBS Dictionary Entry
-- Extended definition for a WBS Element. 1:1 with WBSElement.
CREATE TABLE pmbok.wbs_dictionary_entry (
    wbsd_id UUID NOT NULL PRIMARY KEY,
    wbs_element_id UUID NOT NULL,  -- Linked WBS element.
    description TEXT NOT NULL,  -- Detailed scope of the work package.
    deliverables TEXT NOT NULL,  -- List of deliverables.
    acceptance_criteria TEXT NOT NULL,  -- Acceptance criteria summary.
    predecessors VARCHAR(100)  -- Comma-list of predecessor WBS codes.
);
-- P10  Schedule Activity
-- Time-phased task tied to a WBS Element.
CREATE TABLE pmbok.schedule_activity (
    activity_id UUID NOT NULL PRIMARY KEY,
    wbs_element_id UUID NOT NULL,  -- Linked WBS element.
    activity_code VARCHAR(20) NOT NULL,  -- Activity code.
    name VARCHAR(200) NOT NULL,  -- Task name.
    start_planned DATE NOT NULL,  -- Planned start.
    finish_planned DATE NOT NULL,  -- Planned finish.
    start_actual DATE,  -- Actual start.
    finish_actual DATE,  -- Actual finish.
    duration_days INTEGER NOT NULL,  -- Working days duration.
    owner_person_id UUID NOT NULL,  -- Assigned owner.
    department VARCHAR NOT NULL,  -- Executing department.
    status VARCHAR NOT NULL DEFAULT 'Not started',  -- Activity state.
    pct_complete NUMERIC(5,2) NOT NULL DEFAULT 0  -- Percent complete (0-100).
);
-- P11  Milestone
-- Zero-duration schedule marker.
CREATE TABLE pmbok.milestone (
    milestone_id UUID NOT NULL PRIMARY KEY,
    project_id UUID NOT NULL,  -- Parent project.
    name VARCHAR(200) NOT NULL,  -- Milestone name.
    baseline_date DATE NOT NULL,  -- Baseline target date.
    forecast_date DATE,  -- Current forecast.
    actual_date DATE,  -- Actual date achieved.
    status VARCHAR NOT NULL DEFAULT 'On track',  -- State.
    owner_role VARCHAR(100) NOT NULL  -- Accountable role.
);
-- P12  Schedule Dependency
-- Predecessor/successor link between schedule activities.
CREATE TABLE pmbok.schedule_dependency (
    dependency_id UUID NOT NULL PRIMARY KEY,
    predecessor_activity_id UUID NOT NULL,  -- Predecessor.
    successor_activity_id UUID NOT NULL,  -- Successor.
    relationship VARCHAR NOT NULL DEFAULT 'FS',  -- Dependency type.
    lag_days INTEGER DEFAULT 0  -- Lag (or lead if negative).
);
-- P13  Budget Line Item
-- Cost estimate tied to a WBS Element.
CREATE TABLE pmbok.budget_line_item (
    budget_line_id UUID NOT NULL PRIMARY KEY,
    wbs_element_id UUID NOT NULL,  -- Linked WP.
    category VARCHAR NOT NULL,  -- Cost category.
    labor_amount NUMERIC(12,2) DEFAULT 0,  -- Labor cost.
    materials_amount NUMERIC(12,2) DEFAULT 0,  -- Materials cost.
    vendor_amount NUMERIC(12,2) DEFAULT 0,  -- Vendor / contractor cost.
    other_amount NUMERIC(12,2) DEFAULT 0,  -- Other cost.
    subtotal NUMERIC(12,2) NOT NULL,  -- Sum of components.
    contingency_pct NUMERIC(5,2) NOT NULL DEFAULT 10.00,  -- Contingency percent.
    total NUMERIC(12,2) NOT NULL,  -- Subtotal * (1 + contingency).
    funding_source VARCHAR NOT NULL  -- Funding source.
);
-- P14  Risk
-- Identified risk with L×I scoring.
CREATE TABLE pmbok.risk (
    risk_id UUID NOT NULL PRIMARY KEY,
    project_id UUID NOT NULL,  -- Parent project.
    risk_code VARCHAR(8) NOT NULL,  -- R-NNN, monotonic.
    category VARCHAR NOT NULL,  -- Risk category.
    description TEXT NOT NULL,  -- Risk statement.
    "trigger" TEXT,  -- What would have to happen.
    likelihood SMALLINT NOT NULL,  -- 1-5.
    impact SMALLINT NOT NULL,  -- 1-5.
    score SMALLINT NOT NULL,  -- likelihood * impact (computed).
    response_type VARCHAR NOT NULL,  -- Response strategy.
    owner_person_id UUID NOT NULL,  -- Risk owner.
    department VARCHAR NOT NULL,  -- Owning department.
    due_date DATE,  -- Target mitigation date.
    status VARCHAR NOT NULL DEFAULT 'Open',  -- Risk state.
    residual_score SMALLINT,  -- Score after mitigation.
    compliance_flag VARCHAR  -- Applicable compliance frame.
);
-- P15  Risk Response
-- Mitigation, transfer, avoidance, or acceptance action.
CREATE TABLE pmbok.risk_response (
    response_id UUID NOT NULL PRIMARY KEY,
    risk_id UUID NOT NULL,  -- Parent risk.
    action_type VARCHAR NOT NULL,  -- Action category.
    description TEXT NOT NULL,  -- Action description.
    owner_person_id UUID NOT NULL,  -- Action owner.
    due_date DATE,  -- Target date.
    status VARCHAR NOT NULL DEFAULT 'Open'  -- Action state.
);
-- P16  Communications Audience
-- Audience entry in the Communications Matrix.
CREATE TABLE pmbok.communications_audience (
    comm_audience_id UUID NOT NULL PRIMARY KEY,
    project_id UUID NOT NULL,  -- Parent project.
    audience VARCHAR(100) NOT NULL,  -- Audience name.
    department VARCHAR,  -- Department, if applicable.
    information TEXT NOT NULL,  -- Information communicated.
    format VARCHAR NOT NULL,  -- Format.
    channel VARCHAR NOT NULL,  -- Channel.
    cadence VARCHAR NOT NULL,  -- Frequency.
    owner_role VARCHAR(100) NOT NULL  -- Owner role.
);
-- P17  Meeting Cadence
-- Recurring meeting in the comms plan.
CREATE TABLE pmbok.meeting_cadence (
    cadence_id UUID NOT NULL PRIMARY KEY,
    project_id UUID NOT NULL,  -- Parent project.
    meeting VARCHAR(100) NOT NULL,  -- Meeting name.
    attendees TEXT NOT NULL,  -- Audience description.
    cadence VARCHAR NOT NULL,  -- Frequency.
    duration_min SMALLINT NOT NULL DEFAULT 30,  -- Length in minutes.
    owner_role VARCHAR(100) NOT NULL  -- Meeting owner.
);
-- P18  Quality Standard
-- Standard or regulation governing project quality.
CREATE TABLE pmbok.quality_standard (
    standard_id UUID NOT NULL PRIMARY KEY,
    project_id UUID NOT NULL,  -- Parent project.
    frame VARCHAR NOT NULL,  -- Compliance frame.
    applicability TEXT NOT NULL,  -- Where this standard applies.
    evidence_requirement TEXT NOT NULL  -- Required audit evidence.
);
-- P19  Quality Activity
-- QA (process) or QC (product) activity.
CREATE TABLE pmbok.quality_activity (
    activity_id UUID NOT NULL PRIMARY KEY,
    project_id UUID NOT NULL,  -- Parent project.
    activity_type VARCHAR NOT NULL,  -- QA or QC.
    deliverable VARCHAR(200) NOT NULL,  -- Target deliverable / process.
    method VARCHAR NOT NULL,  -- Method.
    owner_role VARCHAR(100) NOT NULL,  -- Activity owner.
    cadence VARCHAR NOT NULL  -- Frequency.
);
-- P20  Quality Metric
-- Measurable quality KPI.
CREATE TABLE pmbok.quality_metric (
    metric_id UUID NOT NULL PRIMARY KEY,
    project_id UUID NOT NULL,  -- Parent project.
    metric VARCHAR(200) NOT NULL,  -- KPI name.
    target VARCHAR(100) NOT NULL,  -- Target value.
    method VARCHAR(100) NOT NULL,  -- Collection method.
    cadence VARCHAR NOT NULL,  -- Reporting cadence.
    owner_role VARCHAR(100) NOT NULL  -- Owner role.
);
-- P21  Change Request
-- Project-level CR against baselined scope/schedule/cost/quality.
CREATE TABLE pmbok.change_request (
    cr_id UUID NOT NULL PRIMARY KEY,
    project_id UUID NOT NULL,  -- Parent project.
    cr_code VARCHAR(8) NOT NULL,  -- C-NNN.
    intake_id VARCHAR(16),  -- Linked intake.
    requested_at DATE NOT NULL,  -- Submission date.
    requested_by_person_id UUID NOT NULL,  -- Requester.
    cr_class VARCHAR NOT NULL,  -- Class A/B/C/Emergency.
    change_types TEXT NOT NULL,  -- JSON array of types.
    affected_artifacts TEXT NOT NULL,  -- Doc IDs and WBS codes.
    description TEXT NOT NULL,  -- Change requested.
    reason TEXT NOT NULL,  -- Driver / rationale.
    impact_scope TEXT,  -- Scope impact.
    impact_schedule_days INTEGER DEFAULT 0,  -- Schedule delta in days.
    impact_cost NUMERIC(12,2) DEFAULT 0,  -- Cost delta.
    impact_quality TEXT,  -- Quality / compliance impact.
    decision VARCHAR NOT NULL DEFAULT 'Pending',  -- Decision.
    decided_by_person_id UUID,  -- Approver.
    decided_at DATE,  -- Decision date.
    implementation_verified BOOLEAN DEFAULT FALSE,  -- Verified flag.
    linked_artifacts_updated BOOLEAN DEFAULT FALSE,  -- Linked artifacts updated.
    status VARCHAR NOT NULL DEFAULT 'Open'  -- CR lifecycle state.
);
-- P22  Change Impact Assessment
-- Per-department impact statement on a CR.
CREATE TABLE pmbok.change_impact_assessment (
    impact_id UUID NOT NULL PRIMARY KEY,
    cr_id UUID NOT NULL,  -- Parent CR.
    department VARCHAR NOT NULL,  -- Assessing department.
    scope_impact TEXT,  -- Scope impact statement.
    schedule_impact_days INTEGER,  -- Schedule delta.
    cost_impact NUMERIC(12,2),  -- Cost delta.
    quality_impact TEXT,  -- Quality / compliance impact.
    submitted_by_person_id UUID NOT NULL,  -- Assessor.
    submitted_at DATE NOT NULL  -- Assessment date.
);
-- P23  Status Report
-- Recurring snapshot of project health.
CREATE TABLE pmbok.status_report (
    report_id UUID NOT NULL PRIMARY KEY,
    project_id UUID NOT NULL,  -- Parent project.
    period_start DATE NOT NULL,  -- Reporting period start.
    period_end DATE NOT NULL,  -- Reporting period end.
    overall_status VARCHAR NOT NULL DEFAULT 'Green',  -- G/Y/R.
    trend VARCHAR NOT NULL DEFAULT 'Steady',  -- Trend.
    executive_summary TEXT NOT NULL,  -- 3-5 sentence narrative.
    decisions_needed TEXT,  -- Decisions list.
    submitted_by_person_id UUID NOT NULL,  -- PM submitting.
    submitted_at TIMESTAMPTZ NOT NULL  -- Submission timestamp.
);
-- P24  Status Report Knowledge-Area
-- Per-knowledge-area health entry within a status report.
CREATE TABLE pmbok.status_report_area (
    area_id UUID NOT NULL PRIMARY KEY,
    report_id UUID NOT NULL,  -- Parent report.
    knowledge_area VARCHAR NOT NULL,  -- KA.
    status VARCHAR NOT NULL DEFAULT 'Green',  -- G/Y/R.
    commentary TEXT  -- Commentary for the area.
);
-- P25  Lesson Learned
-- Captured learning from project execution.
CREATE TABLE pmbok.lesson_learned (
    lesson_id UUID NOT NULL PRIMARY KEY,
    project_id UUID NOT NULL,  -- Parent project.
    category VARCHAR NOT NULL,  -- Lesson category.
    departments TEXT,  -- Comma-list of departments.
    lesson VARCHAR(300) NOT NULL,  -- 1-sentence lesson.
    what_happened TEXT NOT NULL,  -- What / when / who.
    recommendation TEXT NOT NULL,  -- Action for next time.
    followup_owner_role VARCHAR(100),  -- Follow-up owner.
    status VARCHAR NOT NULL DEFAULT 'Open'  -- Lesson state.
);
-- P26  Closure Checklist Item
-- One item from the project closure checklist.
CREATE TABLE pmbok.closure_checklist_item (
    closure_item_id UUID NOT NULL PRIMARY KEY,
    project_id UUID NOT NULL,  -- Parent project.
    item VARCHAR(300) NOT NULL,  -- Checklist item text.
    owner_role VARCHAR(100) NOT NULL,  -- Owner role.
    done BOOLEAN NOT NULL DEFAULT FALSE,  -- Done flag.
    evidence TEXT  -- Evidence path/system.
);
-- P27  Assumption
-- Project assumption.
CREATE TABLE pmbok.assumption (
    assumption_id UUID NOT NULL PRIMARY KEY,
    project_id UUID NOT NULL,  -- Parent project.
    code VARCHAR(8) NOT NULL,  -- A-NNN.
    description TEXT NOT NULL,  -- Assumption statement.
    verified BOOLEAN NOT NULL DEFAULT FALSE  -- Verified flag.
);
-- P28  Constraint
-- Project constraint (budget, schedule, regulatory, etc.).
CREATE TABLE pmbok.constraint (
    constraint_id UUID NOT NULL PRIMARY KEY,
    project_id UUID NOT NULL,  -- Parent project.
    code VARCHAR(8) NOT NULL,  -- CN-NNN.
    constraint_type VARCHAR NOT NULL,  -- Type.
    description TEXT NOT NULL  -- Constraint statement.
);
-- P29  Decision
-- Logged project decision with rationale.
CREATE TABLE pmbok.decision (
    decision_id UUID NOT NULL PRIMARY KEY,
    project_id UUID NOT NULL,  -- Parent project.
    code VARCHAR(8) NOT NULL,  -- D-NNN.
    decision TEXT NOT NULL,  -- Decision statement.
    rationale TEXT NOT NULL,  -- Rationale.
    decided_by_person_id UUID NOT NULL,  -- Decider.
    decided_at DATE NOT NULL  -- Decision date.
);
-- P30  Approval Signature
-- Signature record for a baselined artifact under 21 CFR Part 11.
CREATE TABLE pmbok.approval (
    approval_id UUID NOT NULL PRIMARY KEY,
    artifact_doc_id VARCHAR(30) NOT NULL,  -- DM-side doc the approval applies to.
    approver_person_id UUID NOT NULL,  -- Approver.
    signature_meaning VARCHAR NOT NULL,  -- 21 CFR §11.50 meaning.
    signed_at TIMESTAMPTZ NOT NULL,  -- Signature timestamp.
    esig_hash VARCHAR(128)  -- E-signature hash.
);
-- P31  Project Team Member
-- Person assigned to the project team.
CREATE TABLE pmbok.project_team_member (
    team_member_id UUID NOT NULL PRIMARY KEY,
    project_id UUID NOT NULL,  -- Parent project.
    person_id UUID NOT NULL,  -- Person.
    role VARCHAR(100) NOT NULL,  -- Role on the team.
    department VARCHAR NOT NULL,  -- Person's department.
    allocation_pct NUMERIC(5,2) NOT NULL DEFAULT 100,  -- Allocation 0-100.
    start_date DATE NOT NULL,  -- On-team start.
    end_date DATE  -- Off-team date.
);
