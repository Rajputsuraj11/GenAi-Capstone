import json
import re
from typing import List
from pipeline.state import ComplianceState, Finding
from pipeline.nodes import call_groq_pii


def pii_check_node(state: ComplianceState) -> ComplianceState:
    """
    Agent 1: Detect PII (emails, phones, SSNs, addresses, names).
    Uses both regex pre-screening AND Groq LLaMA for contextual PII.
    """
    pages = state["pages"]
    rules = state["rules"].get("pii", {})
    findings: List[Finding] = []

    regex_patterns = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
        "phone": r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
        "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
    }

    # Build enabled/disabled PII type lists from rules so AI respects them too
    # Maps rule flag -> (pii_type_label, pii_type_key)
    pii_type_map = [
        ("check_emails",  "Email addresses",                      "email"),
        ("check_phones",  "Phone numbers",                        "phone"),
        ("check_ssn",     "Social Security Numbers / National IDs","ssn"),
        ("check_names",   "Full names (especially with other info)","name"),
    ]
    # These types are always checked (not exposed as toggles in the UI)
    always_checked = [
        "Physical addresses",
        "Date of birth",
        "Financial account numbers",
        "Medical information",
    ]

    enabled_types: List[str] = []
    disabled_types: List[str] = []

    for flag, label, _ in pii_type_map:
        if rules.get(flag, True):
            enabled_types.append(label)
        else:
            disabled_types.append(label)

    enabled_types.extend(always_checked)

    for page in pages:
        if page["is_empty"]:
            continue

        text = page["text"]
        page_num = page["page_number"]
        local_findings = []

        # Regex pre-screening — already respects rule flags
        for pii_type, pattern in regex_patterns.items():
            if not rules.get(f"check_{pii_type}s", True):
                continue
            matches = re.findall(pattern, text)
            valid_matches = [m for m in matches if m and len(str(m).strip()) > 0][:3]
            if valid_matches:
                local_findings.append({
                    "type": pii_type,
                    "matches": valid_matches,
                    "method": "regex"
                })

        # Build dynamic prompt that explicitly tells AI what to check / skip
        text_snippet = text[:3000]

        enabled_list  = "\n".join(f"- {t}" for t in enabled_types)
        disabled_block = (
            "\n\nDO NOT flag or report any of the following — they are disabled by policy:\n"
            + "\n".join(f"- {t}" for t in disabled_types)
            if disabled_types else ""
        )

        prompt = (
            f"You are a data privacy compliance officer. Analyze the following text from page {page_num} of a PDF.\n\n"
            f"TASK: Identify ONLY the PII types listed under CHECK below. "
            f"Ignore everything under DO NOT CHECK.\n\n"
            f"CHECK for these PII types:\n{enabled_list}"
            f"{disabled_block}\n\n"
            f"TEXT TO ANALYZE:\n\"\"\"\n{text_snippet}\n\"\"\"\n\n"
            "Respond in this EXACT JSON format only (no extra text):\n"
            '{\n  "has_pii": true/false,\n  "findings": [\n    {\n'
            '      "pii_type": "email/phone/name/address/ssn/other",\n'
            '      "severity": "HIGH/MEDIUM/LOW",\n'
            '      "description": "brief description",\n'
            '      "evidence": "masked evidence e.g. j***@example.com"\n'
            "    }\n  ]\n}"
        )

        groq_response = call_groq_pii(prompt)

        if groq_response.startswith("ERROR:"):
            findings.append(Finding(
                page_number=page_num,
                check_type="PII",
                severity="LOW",
                description=f"Groq API Error: {groq_response[:100]}",
                evidence="AI analysis failed - check API key",
                flagged=True
            ))
        else:
            try:
                clean = groq_response.strip().replace("```json", "").replace("```", "")
                clean = clean.replace('\n', ' ').replace('\r', '')
                if clean.count('{') > clean.count('}'):
                    clean += '}'
                if clean.count('"') % 2 != 0:
                    clean += '"'

                result = json.loads(clean)

                if result.get("has_pii"):
                    for f in result.get("findings", []):
                        # Secondary guard: drop findings for disabled PII types
                        pii_type_key = f.get("pii_type", "").lower()
                        if pii_type_key == "email" and not rules.get("check_emails", True):
                            continue
                        if pii_type_key == "phone" and not rules.get("check_phones", True):
                            continue
                        if pii_type_key == "ssn" and not rules.get("check_ssn", True):
                            continue
                        if pii_type_key == "name" and not rules.get("check_names", True):
                            continue

                        findings.append(Finding(
                            page_number=page_num,
                            check_type="PII",
                            severity=f.get("severity", "MEDIUM"),
                            description=f"[AI] {f.get('description', '')}",
                            evidence=f.get("evidence", ""),
                            flagged=True
                        ))
                else:
                    findings.append(Finding(
                        page_number=page_num,
                        check_type="PII",
                        severity="LOW",
                        description="[AI] No PII detected by Groq",
                        evidence="Clean",
                        flagged=False
                    ))
            except (json.JSONDecodeError, KeyError) as e:
                findings.append(Finding(
                    page_number=page_num,
                    check_type="PII",
                    severity="MEDIUM",
                    description=f"[AI] Parse error: {str(e)[:50]}",
                    evidence=f"Raw: {groq_response[:150]}",
                    flagged=True
                ))

        # Add regex findings, avoiding duplicates with AI findings
        regex_evidences = set()
        for ai_finding in findings:
            if isinstance(ai_finding, dict) and ai_finding.get('evidence') and "Pattern matches" not in ai_finding.get('evidence', ''):
                regex_evidences.add(ai_finding.get('evidence', '').lower())

        for rf in local_findings:
            regex_evidence = f"Pattern matches found: {str(rf['matches'])[:100]}"
            if not any(regex_evidence.lower() in existing_evidence for existing_evidence in regex_evidences):
                findings.append(Finding(
                    page_number=page_num,
                    check_type="PII",
                    severity="HIGH",
                    description=f"Regex-detected {rf['type'].upper()}",
                    evidence=regex_evidence,
                    flagged=True
                ))

    state["pii_findings"] = findings
    return state