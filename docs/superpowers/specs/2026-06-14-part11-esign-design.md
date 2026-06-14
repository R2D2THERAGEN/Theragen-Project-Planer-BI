# True 21 CFR Part 11 E-Signing — Scoping & Recommendation

Status: design / scoping (2026-06-14). Compliance-hardening track. This documents **why** the 2c-5
document approvals are an honest **attestation, not a §11 signature**, what a true §11 ceremony would
require, the realistic options, and a recommendation. It is analysis — not a build.

## Where we are (2c-5)

A document approval today is a row in the **Document Approvals** List that the nightly sync turns into
`doc_mgmt.document_approval` with `esig_hash = SHA-256(doc_id | version | approver_email | meaning |
signed_at)`, `signed_at` = the List item's `createdDateTime`, `ip_address = NULL`. Every surface labels
it **"Attestation (non-§11)"**. It provides **traceability** (the hash recomputes from the stored row,
so the record is tamper-evident *as recorded*) but not signer-controlled, identity-verified
non-repudiation.

## What 21 CFR Part 11 actually requires (paraphrased)

| § | Requirement | The attestation today |
|---|-------------|------------------------|
| 11.50 | Signature manifestation: printed name, date/time, and **meaning** of the signing | ✅ name, time, meaning are recorded |
| 11.70 | Signature-to-record **linking** — a signature cannot be excised, copied, or transferred to falsify | ⚠️ hash binds *metadata* (doc id/version/meaning/time), **not the document's content bytes**; the file could change under it |
| 11.100 | Each signature **unique to one individual**, with **verified identity** | ❌ identity is whoever typed into a SharePoint List; not verified at signing |
| 11.200(a) | Non-biometric signing uses **≥2 components** (e.g. ID + password); re-auth controls within a session | ❌ no re-authentication at the moment of signing |
| 11.10 / 11.300 | Closed-system controls, validated system, ID/password controls | ❌ SharePoint + nightly sync is not a validated signing system |

**Why this architecture can't close the gap:** the "signing" act is *typing into a List*, and the
binding event happens **hours later in a batch job** — not a witnessed, re-authenticated, content-bound
act by the signer. No amount of hashing fixes that the signer never authenticated *at signing* and the
record isn't bound to the document's actual bytes.

## Options

1. **Keep the honest attestation (status quo).** Document the decision: these PMO approvals are
   *governance traceability*, and any record that legally needs a §11 signature lives in the validated
   QMS, not here. Lowest cost. Appropriate **if §11 is not a regulatory requirement for these specific
   records.**
2. **Integrate a validated e-signature provider** (DocuSign CFR Part 11 module, Adobe Acrobat Sign for
   Life Sciences, etc.). The provider runs the §11 ceremony (verified identity, re-auth, witnessed
   signing, content binding, validated + audited). The PMO model stores the provider's **envelope id +
   completion status + signer + signed_at**; `bi.document_approval` shows "Signed (DocuSign §11)" and
   links out. **Least-risk path to actual compliance** — you inherit the provider's validation and
   audit instead of owning it.
3. **Build a Microsoft-native signing step.** A Power App / web "Sign" button that (a) re-authenticates
   the signer via **Entra MFA at signing**, (b) a backend Function verifies the token (verified
   identity), computes a hash over the **actual document file** (content binding), records a
   server-witnessed timestamp + meaning, and writes a tamper-evident signature row. Buildable on the
   stack you have — but **you own the §11 validation, the ID/password controls (11.300), and the
   audited system qualification**, which is a real, ongoing burden.

## Recommendation

- **If §11 is genuinely required for these document approvals:** pursue **Option 2 (validated
  provider)**. It is the fastest and lowest-risk route to defensible compliance; building a §11-grade
  signing + validation regime in-house (Option 3) is a program, not a feature.
- **If §11 is *not* required here** (most likely — controlled SOPs/charters tracked for PMO governance,
  while clinical/GxP records sign in the QMS): **keep Option 1**, and replace the implicit gap with an
  **explicit, documented justification** (a one-paragraph control statement: "PMO document approvals
  are governance attestations; §11 signatures for regulated records are executed in <QMS>"). That
  turns the honest label into a defensible policy position.

**Either way the first step is a regulatory-scope decision, not code:** confirm with Quality/Regulatory
whether any record authored in this system requires a §11 signature. That answer selects the option.

## If Option 2 is chosen — sketch (a future sub-stage)

- A **"Document Signatures"** List captures the *request* (doc, version, signer, meaning); the sync
  calls the provider's API to send an envelope; a return field (or a polled status) records the
  envelope id + completion.
- `doc_mgmt.document_approval` gains `esig_provider`, `provider_envelope_id`, `provider_status`; the
  `esig_kind` label becomes "Signed (<provider> §11)" once completed, and reverts the honesty caveat
  only for provider-completed rows. The home-grown `esig_hash` stays for non-§11 attestations.
- Out of scope until the regulatory-scope decision is made.

## Cross-references

- The attestation implementation + honesty bar: `docs/artifact-entry-setup.md` §T.
- The deferral was recorded in the Phase-2 plan ("true §11 signing → post-2c").
