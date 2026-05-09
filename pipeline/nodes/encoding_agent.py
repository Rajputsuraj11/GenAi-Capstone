import chardet
from langdetect import detect, LangDetectException
from typing import List
from pipeline.state import ComplianceState, Finding


def encoding_check_node(state: ComplianceState) -> ComplianceState:
    """
    Agent 3: Check encoding consistency (UTF-8) and language (English only).
    This is a deterministic agent no LLM needed, saves API quota.
    """
    pages = state["pages"]
    rules = state["rules"].get("encoding", {})
    findings: List[Finding] = []

    allowed_languages = rules.get("allowed_languages", ["en"])
    required_encoding = rules.get("required_encoding", "utf-8")

    for page in pages:
        if page["is_empty"]:
            continue

        text = page["text"]
        page_num = page["page_number"]

        detected_enc = page.get("detected_encoding", "").lower()
        if detected_enc and required_encoding not in detected_enc:
            findings.append(Finding(
                page_number=page_num,
                check_type="ENCODING",
                severity="MEDIUM",
                description=f"Non-UTF-8 encoding detected: {detected_enc}",
                evidence=f"Detected: {detected_enc}, Required: {required_encoding}",
                flagged=True
            ))

        non_printable = sum(1 for c in text if ord(c) > 127 and not c.isprintable())
        max_non_printable = rules.get("max_non_printable", 10)
        if non_printable > max_non_printable:
            findings.append(Finding(
                page_number=page_num,
                check_type="ENCODING",
                severity="LOW",
                description=f"Non-printable characters detected ({non_printable} chars)",
                evidence=f"{non_printable} non-printable characters found on this page",
                flagged=True
            ))

        if len(text.strip()) > 50:
            try:
                lang = detect(text)
                if lang not in allowed_languages:
                    findings.append(Finding(
                        page_number=page_num,
                        check_type="ENCODING",
                        severity="HIGH",
                        description=f"Non-English language detected: '{lang}'",
                        evidence=f"Detected language code: {lang} (allowed: {allowed_languages})",
                        flagged=True
                    ))
            except LangDetectException:
                findings.append(Finding(
                    page_number=page_num,
                    check_type="ENCODING",
                    severity="LOW",
                    description="Language could not be determined",
                    evidence="langdetect was unable to identify the language",
                    flagged=True
                ))

    state["encoding_findings"] = findings
    return state
