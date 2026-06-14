"""Emit the Theragen governance / document paginated reports (.rdl).

Four pixel-perfect, print-ready records, all bound to the published Power BI
semantic model via DAX (same connection as build_paginated.py - no duplicated
logic, paginated and interactive can never disagree):

  1. Theragen Governance Dossier.rdl        - per-document packet (@DocID)
  2. Theragen Governance CR Register.rdl     - all governance change requests
  3. Theragen Controlled Document Register.rdl - the controlled-document portfolio
  4. Theragen Baseline & Phase Gate Register.rdl - baselines + gates (@ProjectCode)

After the semantic model is republished (the new governance tables must exist in
the published model for these DAX datasets to resolve), open each .rdl in Power
BI Report Builder, repoint the TheragenModel data source at the published model,
and publish to the same workspace. Regenerate after edits:
    python tools/build_paginated_governance.py
"""
import os
from xml.dom import minidom

import paginated_lib as pl

OUTDIR = os.path.join(pl.ROOT, "paginated")

DATE = {"DateTime": "DateTime"}
F = "=Fields!{}.Value".format


def _scoped(ds):
    """Dataset-scoped field accessor for standalone textboxes (avoids
    rsFieldReferenceAmbiguous in multi-dataset reports)."""
    return lambda name: f'=First(Fields!{name}.Value, "{ds}")'


# =========================================================================
# 1. Per-Document Governance Dossier (@DocID)
# =========================================================================
def dossier():
    H = _scoped("DsDocHeader")
    datasets = [
        pl.dataset_xml("DsDocList",
            "EVALUATE SELECTCOLUMNS('Controlled Document', "
            "\"DocID\", 'Controlled Document'[Doc ID], "
            "\"DocLabel\", 'Controlled Document'[Doc ID] & \" - \" & 'Controlled Document'[Title]) "
            "ORDER BY [DocID]",
            ["DocID", "DocLabel"]),
        pl.dataset_xml("DsDocHeader",
            "EVALUATE CALCULATETABLE(ROW("
            "\"Title\", SELECTEDVALUE('Controlled Document'[Title]), "
            "\"Subtitle\", SELECTEDVALUE('Controlled Document'[Subtitle]), "
            "\"DocType\", SELECTEDVALUE('Controlled Document'[Document Type]), "
            "\"Dept\", SELECTEDVALUE('Controlled Document'[Department]), "
            "\"Phase\", SELECTEDVALUE('Controlled Document'[Lifecycle Phase]), "
            "\"Status\", SELECTEDVALUE('Controlled Document'[Status]), "
            "\"Version\", SELECTEDVALUE('Controlled Document'[Current Version]), "
            "\"Owner\", SELECTEDVALUE('Controlled Document'[Owner]), "
            "\"Approver\", SELECTEDVALUE('Controlled Document'[Approver]), "
            "\"ReviewCycle\", SELECTEDVALUE('Controlled Document'[Review Cycle]), "
            "\"NextReview\", SELECTEDVALUE('Controlled Document'[Next Review Due]), "
            "\"Classification\", SELECTEDVALUE('Controlled Document'[Classification])), "
            "TREATAS({@DocID}, 'Controlled Document'[Doc ID]))",
            ["Title", "Subtitle", "DocType", "Dept", "Phase", "Status", "Version",
             "Owner", "Approver", "ReviewCycle", "NextReview", "Classification"],
            params=["DocID"], types={"NextReview": "DateTime"}),
        pl.dataset_xml("DsRaci",
            "EVALUATE SELECTCOLUMNS(CALCULATETABLE('Document RACI', "
            "TREATAS({@DocID}, 'Controlled Document'[Doc ID])), "
            "\"Role\", 'Document RACI'[Role Name], "
            "\"Dept\", 'Document RACI'[Department], "
            "\"Touchpoint\", 'Document RACI'[Touchpoint], "
            "\"ValidFrom\", 'Document RACI'[Valid From], "
            "\"ValidTo\", 'Document RACI'[Valid To]) ORDER BY [Role], [Dept]",
            ["Role", "Dept", "Touchpoint", "ValidFrom", "ValidTo"],
            params=["DocID"], types={"ValidFrom": "DateTime", "ValidTo": "DateTime"}),
        pl.dataset_xml("DsVersions",
            "EVALUATE SELECTCOLUMNS(CALCULATETABLE('Document Version', "
            "TREATAS({@DocID}, 'Controlled Document'[Doc ID])), "
            "\"Version\", 'Document Version'[Version], "
            "\"Status\", 'Document Version'[Status], "
            "\"ChangeSummary\", 'Document Version'[Change Summary], "
            "\"ChangeClass\", 'Document Version'[Change Class], "
            "\"Author\", 'Document Version'[Author], "
            "\"EffectiveDate\", 'Document Version'[Effective Date], "
            "\"LinkedCR\", 'Document Version'[Linked CR]) ORDER BY [Version]",
            ["Version", "Status", "ChangeSummary", "ChangeClass", "Author",
             "EffectiveDate", "LinkedCR"],
            params=["DocID"], types={"EffectiveDate": "DateTime"}),
        pl.dataset_xml("DsApprovals",
            "EVALUATE SELECTCOLUMNS(CALCULATETABLE('Document Approval', "
            "TREATAS({@DocID}, 'Controlled Document'[Doc ID])), "
            "\"Version\", 'Document Approval'[Version], "
            "\"Approver\", 'Document Approval'[Approver], "
            "\"Meaning\", 'Document Approval'[Signature Meaning], "
            "\"SignedAt\", 'Document Approval'[Signed At], "
            "\"Kind\", 'Document Approval'[Attestation Kind], "
            "\"Hash\", 'Document Approval'[Attestation Hash]) ORDER BY [Version]",
            ["Version", "Approver", "Meaning", "SignedAt", "Kind", "Hash"],
            params=["DocID"], types={"SignedAt": "DateTime"}),
        pl.dataset_xml("DsCRs",
            "EVALUATE SELECTCOLUMNS(CALCULATETABLE('Governance Change Request', "
            "TREATAS({@DocID}, 'Controlled Document'[Doc ID])), "
            "\"CRCode\", 'Governance Change Request'[CR Code], "
            "\"Class\", 'Governance Change Request'[CR Class], "
            "\"Description\", 'Governance Change Request'[Description], "
            "\"Decision\", 'Governance Change Request'[Decision], "
            "\"Status\", 'Governance Change Request'[Status], "
            "\"DecidedBy\", 'Governance Change Request'[Decided By], "
            "\"DecidedDate\", 'Governance Change Request'[Decided Date]) ORDER BY [CRCode]",
            ["CRCode", "Class", "Description", "Decision", "Status", "DecidedBy",
             "DecidedDate"],
            params=["DocID"], types={"DecidedDate": "DateTime"}),
    ]
    b = []
    b.append(pl.logo_image())
    b.append(pl.label_value_box("HdrDoc", "CONTROLLED DOCUMENT DOSSIER",
             '=Parameters!DocID.Value', 1.58, 0, 3.2, 0.5, vsize="13pt"))
    b.append(pl.label_value_box("HdrTitle", "TITLE", H("Title"), 4.85, 0, 3.2, 0.5))
    b.append(pl.label_value_box("HdrStatus", "STATUS", H("Status"), 8.1, 0, 1.0, 0.5))
    b.append(pl.label_value_box("HdrVer", "VERSION", H("Version"), 9.15, 0, 1.15, 0.5))
    # metadata strip
    meta = [("Document Type", "DocType"), ("Department", "Dept"),
            ("Lifecycle Phase", "Phase"), ("Owner", "Owner"),
            ("Approver", "Approver"), ("Review Cycle", "ReviewCycle"),
            ("Next Review Due", "NextReview"), ("Classification", "Classification")]
    x = 0.0
    w = 10.3 / 4
    for i, (lab, fld) in enumerate(meta):
        left = (i % 4) * w
        top = 0.6 + (i // 4) * 0.5
        val = (f'=Format(First(Fields!NextReview.Value, "DsDocHeader"), "yyyy-MM-dd")'
               if fld == "NextReview" else H(fld))
        b.append(pl.label_value_box(f"meta{i}", lab, val, left, top, w - 0.04, 0.46,
                                    vsize="8.5pt", vbold=False))
    y = 1.7
    b.append(pl.section_title("secRaci", "RACI - responsibility assignment", 0, y, 10.3))
    b.append(pl.tablix("Raci", "DsRaci", [
        ("Role", F("Role"), 1.6, "Left"),
        ("Department", F("Dept"), 2.2, "Left"),
        ("Touchpoint", F("Touchpoint"), 4.3, "Left"),
        ("Valid From", F("ValidFrom"), 1.1, "Center", "yyyy-MM-dd"),
        ("Valid To", F("ValidTo"), 1.1, "Center", "yyyy-MM-dd"),
    ], 0, y + 0.26, 10.3, no_rows="No RACI assignments recorded for this document."))
    y += 1.2
    b.append(pl.section_title("secVer", "Version history", 0, y, 10.3))
    b.append(pl.tablix("Versions", "DsVersions", [
        ("Version", F("Version"), 0.8, "Center"),
        ("Status", F("Status"), 1.1, "Center"),
        ("Change Summary", F("ChangeSummary"), 4.1, "Left"),
        ("Class", F("ChangeClass"), 1.5, "Left"),
        ("Author", F("Author"), 1.6, "Left"),
        ("Effective", F("EffectiveDate"), 1.2, "Center", "yyyy-MM-dd"),
        ("Linked CR", F("LinkedCR"), 1.0, "Center", None, pl.TEAL, True),
    ], 0, y + 0.26, 10.3, sort_field="Version",
        no_rows="No versions recorded for this document."))
    y += 1.2
    b.append(pl.section_title("secApp",
             "Approval attestations  (non-21 CFR Part 11 - server-computed traceability)", 0, y, 10.3))
    b.append(pl.tablix("Approvals", "DsApprovals", [
        ("Version", F("Version"), 0.8, "Center"),
        ("Approver", F("Approver"), 1.8, "Left"),
        ("Meaning", F("Meaning"), 1.2, "Left"),
        ("Signed At", F("SignedAt"), 1.5, "Center", "yyyy-MM-dd HH:mm"),
        ("Attestation Kind", F("Kind"), 1.8, "Left"),
        ("Attestation Hash (SHA-256)", F("Hash"), 3.2, "Left", None, "#605E5C"),
    ], 0, y + 0.26, 10.3, no_rows="No approval attestations recorded."))
    y += 1.2
    b.append(pl.section_title("secCR", "Governance change requests against this document", 0, y, 10.3))
    b.append(pl.tablix("CRs", "DsCRs", [
        ("CR Code", F("CRCode"), 1.0, "Left", None, pl.TEAL, True),
        ("Class", F("Class"), 1.5, "Left"),
        ("Description", F("Description"), 3.5, "Left"),
        ("Decision", F("Decision"), 1.1, "Center", None, pl.DECISION_COLOR, True),
        ("Status", F("Status"), 1.2, "Center", None, pl.CRSTATUS_COLOR, True),
        ("Decided By", F("DecidedBy"), 1.6, "Left"),
        ("Decided", F("DecidedDate"), 1.1, "Center", "yyyy-MM-dd"),
    ], 0, y + 0.26, 10.3, sort_field="CRCode",
        no_rows="No governance change requests target this document."))
    rdl = pl.build_rdl(
        report_id_seed="thg-bi/paginated/governance-dossier",
        datasets=datasets, body_items=b, body_height=y + 1.4, body_width=10.3,
        parameters=[pl.picker_parameter("DocID", "Document", "DsDocList", "DocID", "DocLabel")])
    return "Theragen Governance Dossier.rdl", rdl


# =========================================================================
# 2. Governance Change Control Register (all CHG-NNN)
# =========================================================================
def cr_register():
    datasets = [
        pl.dataset_xml("DsCRs",
            "EVALUATE SELECTCOLUMNS('Governance Change Request', "
            "\"CRCode\", 'Governance Change Request'[CR Code], "
            "\"DocID\", 'Governance Change Request'[Doc ID], "
            "\"DocTitle\", 'Governance Change Request'[Doc Title], "
            "\"Class\", 'Governance Change Request'[CR Class], "
            "\"RequestedBy\", 'Governance Change Request'[Requested By], "
            "\"RequestedDate\", 'Governance Change Request'[Requested Date], "
            "\"Decision\", 'Governance Change Request'[Decision], "
            "\"DecidedBy\", 'Governance Change Request'[Decided By], "
            "\"DecidedDate\", 'Governance Change Request'[Decided Date], "
            "\"Status\", 'Governance Change Request'[Status]) ORDER BY [CRCode]",
            ["CRCode", "DocID", "DocTitle", "Class", "RequestedBy", "RequestedDate",
             "Decision", "DecidedBy", "DecidedDate", "Status"],
            types={"RequestedDate": "DateTime", "DecidedDate": "DateTime"}),
        pl.dataset_xml("DsAssess",
            "EVALUATE SELECTCOLUMNS('Governance Change Assessment', "
            "\"CRCode\", 'Governance Change Assessment'[CR Code], "
            "\"DocID\", 'Governance Change Assessment'[Doc ID], "
            "\"Dept\", 'Governance Change Assessment'[Department], "
            "\"Impact\", 'Governance Change Assessment'[Impact Summary], "
            "\"Compliance\", 'Governance Change Assessment'[Compliance Impact], "
            "\"SubmittedDate\", 'Governance Change Assessment'[Submitted Date]) "
            "ORDER BY [CRCode], [Dept]",
            ["CRCode", "DocID", "Dept", "Impact", "Compliance", "SubmittedDate"],
            types={"SubmittedDate": "DateTime"}),
    ]
    b = [pl.logo_image(),
         pl.label_value_box("Hdr", "GOVERNANCE CHANGE CONTROL REGISTER",
                            '="All controlled-document change requests (CHG-NNN)"',
                            1.58, 0, 8.5, 0.5, vsize="13pt")]
    b.append(pl.section_title("secCR", "Governance change requests", 0, 0.6, 10.3))
    b.append(pl.tablix("CRs", "DsCRs", [
        ("CR Code", F("CRCode"), 0.9, "Left", None, pl.TEAL, True),
        ("Document", F("DocID"), 1.5, "Left"),
        ("Document Title", F("DocTitle"), 2.4, "Left"),
        ("Class", F("Class"), 1.3, "Left"),
        ("Requested By", F("RequestedBy"), 1.4, "Left"),
        ("Requested", F("RequestedDate"), 1.0, "Center", "yyyy-MM-dd"),
        ("Decision", F("Decision"), 1.0, "Center", None, pl.DECISION_COLOR, True),
        ("Decided By", F("DecidedBy"), 1.4, "Left"),
        ("Decided", F("DecidedDate"), 1.0, "Center", "yyyy-MM-dd"),
        ("Status", F("Status"), 1.1, "Center", None, pl.CRSTATUS_COLOR, True),
    ], 0, 0.86, 10.3, sort_field="CRCode", no_rows="No governance change requests."))
    b.append(pl.section_title("secAssess", "Department impact assessments", 0, 2.1, 10.3))
    b.append(pl.tablix("Assess", "DsAssess", [
        ("CR Code", F("CRCode"), 0.9, "Left", None, pl.TEAL, True),
        ("Document", F("DocID"), 1.5, "Left"),
        ("Department", F("Dept"), 1.8, "Left"),
        ("Impact Summary", F("Impact"), 3.2, "Left"),
        ("Compliance Impact", F("Compliance"), 2.9, "Left"),
        ("Submitted", F("SubmittedDate"), 1.0, "Center", "yyyy-MM-dd"),
    ], 0, 2.36, 10.3, sort_field="CRCode",
        no_rows="No department assessments recorded."))
    rdl = pl.build_rdl(report_id_seed="thg-bi/paginated/gov-cr-register",
                       datasets=datasets, body_items=b, body_height=3.7, body_width=10.3)
    return "Theragen Governance CR Register.rdl", rdl


# =========================================================================
# 3. Controlled-Document Register (the portfolio)
# =========================================================================
def doc_register():
    datasets = [
        pl.dataset_xml("DsDocs",
            "EVALUATE SELECTCOLUMNS('Controlled Document', "
            "\"DocID\", 'Controlled Document'[Doc ID], "
            "\"Title\", 'Controlled Document'[Title], "
            "\"DocType\", 'Controlled Document'[Document Type], "
            "\"Dept\", 'Controlled Document'[Department], "
            "\"Phase\", 'Controlled Document'[Lifecycle Phase], "
            "\"Status\", 'Controlled Document'[Status], "
            "\"Version\", 'Controlled Document'[Current Version], "
            "\"Owner\", 'Controlled Document'[Owner], "
            "\"Approver\", 'Controlled Document'[Approver], "
            "\"ReviewCycle\", 'Controlled Document'[Review Cycle], "
            "\"NextReview\", 'Controlled Document'[Next Review Due]) ORDER BY [DocID]",
            ["DocID", "Title", "DocType", "Dept", "Phase", "Status", "Version",
             "Owner", "Approver", "ReviewCycle", "NextReview"],
            types={"NextReview": "DateTime"}),
    ]
    b = [pl.logo_image(),
         pl.label_value_box("Hdr", "CONTROLLED DOCUMENT REGISTER",
                            '="All org-wide controlled documents"', 1.58, 0, 8.5, 0.5,
                            vsize="13pt")]
    b.append(pl.tablix("Docs", "DsDocs", [
        ("Doc ID", F("DocID"), 1.5, "Left", None, pl.TEAL, True),
        ("Title", F("Title"), 2.4, "Left"),
        ("Type", F("DocType"), 1.3, "Left"),
        ("Department", F("Dept"), 1.6, "Left"),
        ("Phase", F("Phase"), 1.2, "Left"),
        ("Status", F("Status"), 0.9, "Center"),
        ("Ver", F("Version"), 0.6, "Center"),
        ("Owner", F("Owner"), 1.4, "Left"),
        ("Approver", F("Approver"), 1.4, "Left"),
        ("Review", F("ReviewCycle"), 0.9, "Left"),
        ("Next Review", F("NextReview"), 1.1, "Center", "yyyy-MM-dd"),
    ], 0, 0.65, 10.3, sort_field="DocID", no_rows="No controlled documents."))
    rdl = pl.build_rdl(report_id_seed="thg-bi/paginated/doc-register",
                       datasets=datasets, body_items=b, body_height=2.0, body_width=10.3)
    return "Theragen Controlled Document Register.rdl", rdl


# =========================================================================
# 4. Baseline + Phase-Gate Register (@ProjectCode)
# =========================================================================
def baseline_register():
    datasets = [
        pl.dataset_xml("DsProjectList",
            "EVALUATE SELECTCOLUMNS('Project', \"ProjectCode\", 'Project'[Project Code], "
            "\"ProjectName\", 'Project'[Project Name]) ORDER BY [ProjectName]",
            ["ProjectCode", "ProjectName"]),
        pl.dataset_xml("DsBaselines",
            "EVALUATE SELECTCOLUMNS(CALCULATETABLE('Project Baseline', "
            "TREATAS({@ProjectCode}, 'Project'[Project Code])), "
            "\"Type\", 'Project Baseline'[Baseline Type], "
            "\"Version\", 'Project Baseline'[Version], "
            "\"Status\", 'Project Baseline'[Status], "
            "\"ChangeSummary\", 'Project Baseline'[Change Summary], "
            "\"BaselinedBy\", 'Project Baseline'[Baselined By], "
            "\"BaselinedDate\", 'Project Baseline'[Baselined Date], "
            "\"BudgetTotal\", 'Project Baseline'[Baseline Budget Total], "
            "\"ActivityCount\", 'Project Baseline'[Baseline Activity Count]) "
            "ORDER BY [Type], [Version]",
            ["Type", "Version", "Status", "ChangeSummary", "BaselinedBy",
             "BaselinedDate", "BudgetTotal", "ActivityCount"],
            params=["ProjectCode"],
            types={"BaselinedDate": "DateTime", "BudgetTotal": "Decimal",
                   "ActivityCount": "Int64"}),
        pl.dataset_xml("DsGates",
            "EVALUATE SELECTCOLUMNS(CALCULATETABLE('Phase Gate Log', "
            "TREATAS({@ProjectCode}, 'Project'[Project Code])), "
            "\"FromPhase\", 'Phase Gate Log'[From Phase], "
            "\"ToPhase\", 'Phase Gate Log'[To Phase], "
            "\"Decision\", 'Phase Gate Log'[Gate Decision], "
            "\"ApprovedBy\", 'Phase Gate Log'[Approved By], "
            "\"DecidedDate\", 'Phase Gate Log'[Decided Date], "
            "\"Notes\", 'Phase Gate Log'[Gate Notes]) ORDER BY [DecidedDate]",
            ["FromPhase", "ToPhase", "Decision", "ApprovedBy", "DecidedDate", "Notes"],
            params=["ProjectCode"], types={"DecidedDate": "DateTime"}),
    ]
    b = [pl.logo_image(),
         pl.label_value_box("Hdr", "BASELINE & PHASE-GATE REGISTER",
                            '=Parameters!ProjectCode.Value', 1.58, 0, 8.5, 0.5, vsize="13pt")]
    b.append(pl.section_title("secBl", "Project baselines (immutable snapshots)", 0, 0.6, 10.3))
    b.append(pl.tablix("Baselines", "DsBaselines", [
        ("Type", F("Type"), 1.2, "Left"),
        ("Version", F("Version"), 0.9, "Center"),
        ("Status", F("Status"), 1.2, "Center"),
        ("Change Summary", F("ChangeSummary"), 3.6, "Left"),
        ("Baselined By", F("BaselinedBy"), 1.6, "Left"),
        ("Baselined", F("BaselinedDate"), 1.1, "Center", "yyyy-MM-dd"),
        ("Budget Total", F("BudgetTotal"), 1.3, "Right", "$#,##0"),
        ("Activities", F("ActivityCount"), 0.9, "Center", "#,0"),
    ], 0, 0.86, 10.3, sort_field="Version", no_rows="No baselines for this project."))
    b.append(pl.section_title("secGate", "Phase-gate transitions", 0, 2.1, 10.3))
    b.append(pl.tablix("Gates", "DsGates", [
        ("From Phase", F("FromPhase"), 1.8, "Left"),
        ("To Phase", F("ToPhase"), 1.8, "Left"),
        ("Gate Decision", F("Decision"), 2.0, "Left"),
        ("Approved By", F("ApprovedBy"), 1.7, "Left"),
        ("Decided", F("DecidedDate"), 1.1, "Center", "yyyy-MM-dd"),
        ("Gate Notes", F("Notes"), 1.9, "Left"),
    ], 0, 2.36, 10.3, sort_field="DecidedDate", no_rows="No phase gates for this project."))
    rdl = pl.build_rdl(report_id_seed="thg-bi/paginated/baseline-register",
                       datasets=datasets, body_items=b, body_height=3.7, body_width=10.3,
                       parameters=[pl.picker_parameter("ProjectCode", "Project",
                                   "DsProjectList", "ProjectCode", "ProjectName")])
    return "Theragen Baseline & Phase Gate Register.rdl", rdl


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    for fn, rdl in (dossier(), cr_register(), doc_register(), baseline_register()):
        minidom.parseString(rdl)  # fail loudly on malformed XML
        with open(os.path.join(OUTDIR, fn), "w", encoding="utf-8") as f:
            f.write(rdl)
        print(f"  wrote paginated/{fn}  ({len(rdl):,} bytes)")


if __name__ == "__main__":
    main()
