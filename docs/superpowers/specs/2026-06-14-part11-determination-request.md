# 21 CFR Part 11 — Applicability Determination Request

**Status:** OPEN — pending Quality/Regulatory determination.
**Current PMO direction (2026-06-14):** considering integrating this system with the QMS; the §11 approach is **not finalized**. No §11 build proceeds until this determination is signed off.

## Purpose

Determine whether any electronic signature captured by the **Theragen Project Planner BI** system is subject to **21 CFR Part 11**, so the correct e-signature approach is implemented (and so we don't over- or under-build).

## Records that carry a sign-off today

| Record | Table | Today | §11 candidate? |
|---|---|---|---|
| **Document Approval** | `doc_mgmt.document_approval` | non-§11 **attestation** (SHA-256 over `doc_id\|version\|approver\|meaning\|signed_at`) | **YES — the only real candidate** |
| Status-report sign-off | `pmbok.status_report.approved_by/at` | management sign-off | No — PMO governance record |
| CR / governance-CR decision | `change_request(_gov).decided_by/at` | governance decision | No |
| Phase-gate approval | `pmbok.phase_gate_log.approved_by` | governance approval | No |
| Baseline attestation | `pmbok.project_baseline` | governance attestation | No |

## The two-part applicability test (for Quality/Regulatory)

§11 applies to an electronic signature only when **both** are true:

1. **Predicate rule** — an FDA GxP / QSR predicate rule (GMP / GLP / GCP, 21 CFR 820, etc.) *requires* the record to be created and signed.
2. **System of record** — *this* system is the **official record** of that signature, **not** a management/tracking copy of a signature that executes in the validated QMS.

## Decisive factors

- **Internal vs external signers** — if any required signer is **external** (CRO, vendor, contractor), §11 strongly favors a **validated provider**: you cannot run §11.100(b) identity-proofing or §11.300 credential controls for parties outside your tenant. Internal-only signers keep a Microsoft-native ceremony viable.
- **Potential QMS integration (current direction)** — if this system integrates with the validated QMS such that the **QMS becomes the system of record** for controlled-document approvals, then the §11 signatures execute in the QMS and this system holds **management attestations** (→ Path 1). That integration design would supersede Path 2.

## Paths (detailed in `2026-06-14-part11-esign-design.md`)

- **Path 1 — §11 NOT required here** (most likely for a PMO planning system): keep the honest non-§11 attestation + add a one-paragraph **documented control statement** ("PMO approvals here are governance attestations; the official 21 CFR Part 11 signatures execute in `<QMS>`"). Tiny docs change, **no build**.
- **Path 2 — §11 IS required here**: build the **validated e-signature provider** integration (DocuSign Part 11 / Adobe Sign for Life Sciences) — `document_approval` gains `esig_provider` / `provider_envelope_id` / `provider_status`; `esig_kind` becomes "Signed (`<provider>` §11)" only for provider-completed rows. This is a **validation program**, not a feature.

## Decision needed

Quality/Regulatory to confirm, **per record above**, whether §11 applies (both test parts true). The default expectation for a PMO project-planning system is **No** (the QMS owns GxP signatures) → **Path 1**. If the QMS-integration direction is chosen, that integration's design governs how/where §11 signatures are captured.

## Honesty bar (holds regardless)

Until a §11 path is built, **every signature surface in this system is labelled "Attestation (non-§11)"** and must never be presented as a 21 CFR Part 11 signature. This is already enforced in the model (`Document Approval[Attestation Kind]`), the `bi.document_approval` view (`esig_kind`), and the §T docs.
