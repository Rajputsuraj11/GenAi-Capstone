from typing import List, Dict, Any, Optional, TypedDict


class PageData(TypedDict):
    page_number: int
    text: str
    char_count: int
    detected_encoding: str
    encoding_confidence: float
    is_empty: bool


class Finding(TypedDict):
    page_number: int
    check_type: str
    severity: str
    description: str
    evidence: str
    flagged: bool


class ComplianceState(TypedDict):
    pdf_path: str
    pdf_name: str
    pages: List[PageData]
    rules: Dict[str, Any]
    pii_findings: List[Finding]
    confidential_findings: List[Finding]
    encoding_findings: List[Finding]
    abusive_findings: List[Finding]
    all_findings: List[Finding]
    summary: Dict[str, Any]
    report_path: Optional[str]
    error: Optional[str]
