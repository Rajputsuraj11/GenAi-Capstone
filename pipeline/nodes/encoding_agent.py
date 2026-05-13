import chardet
from langdetect import detect, detect_langs, LangDetectException
from typing import List
from pipeline.state import ComplianceState, Finding


def encoding_check_node(state: ComplianceState) -> ComplianceState:
    """
    Agent 3: Check encoding consistency (UTF-8) and language (English only).
    Deterministic — no LLM needed.
    """
    pages = state["pages"]
    rules = state["rules"].get("encoding", {})
    findings: List[Finding] = []

    allowed_languages = rules.get("allowed_languages", ["en"])
    required_encoding = rules.get("required_encoding", "utf-8")
    max_non_printable = rules.get("max_non_printable", 10)

    for page in pages:
        if page["is_empty"]:
            continue

        text = page["text"]
        page_num = page["page_number"]

        # --- Check 1: Encoding ---
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

        # --- Check 2: Non-printable / corrupted characters ---
        # Bug fix: original used `ord(c) > 127 and not c.isprintable()` which
        # misses common corruption markers like the replacement character U+FFFD (■).
        # Now we count both high-byte non-printables AND replacement characters.
        non_printable = sum(
            1 for c in text
            if (ord(c) > 127 and not c.isprintable()) or c == '\ufffd'
        )
        if non_printable > max_non_printable:
            findings.append(Finding(
                page_number=page_num,
                check_type="ENCODING",
                severity="LOW",
                description=f"Non-printable / corrupted characters detected ({non_printable} chars)",
                evidence=f"{non_printable} corrupted/non-printable characters found on this page",
                flagged=True
            ))

        # --- Check 3: Language detection ---
        # Bug fix: original called detect() on the full page text. On mixed-language
        # pages (e.g. mostly English + one Spanish sentence) langdetect picks the
        # dominant language and can return "en", masking the non-English content.
        # Fix: use detect_langs() to get probability scores for all detected languages
        # and flag any non-allowed language that has >= 5% probability.
        if len(text.strip()) > 50:
            try:
                lang_probs = detect_langs(text)  # returns list of Lang objects
                non_allowed = [
                    lp for lp in lang_probs
                    if lp.lang not in allowed_languages and lp.prob >= 0.05
                ]
                if non_allowed:
                    detected_summary = ", ".join(
                        f"{lp.lang}({lp.prob:.0%})" for lp in non_allowed
                    )
                    findings.append(Finding(
                        page_number=page_num,
                        check_type="ENCODING",
                        severity="HIGH",
                        description=f"Non-allowed language(s) detected: {detected_summary}",
                        evidence=f"Languages found: {detected_summary} | Allowed: {allowed_languages}",
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