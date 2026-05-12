from pipeline.state import ComplianceState
from datetime import datetime


def aggregator_node(state: ComplianceState) -> ComplianceState:
    """
    Final node: Merge all findings and compute summary statistics.
    """
    all_findings = (
        state.get("pii_findings", []) +
        state.get("confidential_findings", []) +
        state.get("encoding_findings", []) +
        state.get("abusive_findings", [])
    )

    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    all_findings.sort(key=lambda f: (
        f["page_number"],
        severity_order.get(f["severity"], 3)
    ))

    # FIX 1: Only count/flag pages where flagged=True.
    # The PII agent emits a flagged=False "clean" marker for every passing page —
    # counting those as violations caused flagged_pages to always equal total_pages,
    # making compliance_score permanently 0/100.
    actual_violations = [f for f in all_findings if f.get("flagged", True)]

    total = len(actual_violations)
    by_type = {}
    by_severity = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    flagged_pages = set()

    for f in actual_violations:
        ctype = f["check_type"]
        by_type[ctype] = by_type.get(ctype, 0) + 1
        by_severity[f["severity"]] = by_severity.get(f["severity"], 0) + 1
        flagged_pages.add(f["page_number"])

    total_pages = len(state["pages"])
    clean_pages = total_pages - len(flagged_pages)
    compliance_score = round((clean_pages / total_pages) * 100) if total_pages > 0 else 100

    # FIX 2: Only store actual violations in all_findings (not clean markers).
    # This prevents "No PII detected" rows from appearing in the report table.
    state["all_findings"] = actual_violations

    state["summary"] = {
        "pdf_name": state["pdf_name"],
        "scan_timestamp": datetime.now().isoformat(),
        "total_pages": total_pages,
        "flagged_pages": sorted(list(flagged_pages)),
        "clean_pages": clean_pages,
        "total_findings": total,
        "findings_by_type": by_type,
        "findings_by_severity": by_severity,
        "compliance_score": compliance_score,
        # FIX 3: overall_status was also wrong — total included clean markers,
        # so it was never 0 even on a fully clean document.
        "overall_status": "PASS" if total == 0 else ("FAIL" if by_severity["HIGH"] > 0 else "REVIEW"),
    }

    return state