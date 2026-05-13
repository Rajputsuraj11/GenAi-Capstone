import json
from typing import List
from pipeline.state import ComplianceState, Finding
from pipeline.nodes import call_groq_confidential


def confidential_check_node(state: ComplianceState) -> ComplianceState:
    """
    Agent 2: Detect confidential/proprietary company information.
    Looks for trade secrets, internal IPs, unreleased product info, etc.
    """
    pages = state["pages"]
    rules = state["rules"].get("confidential", {})
    findings: List[Finding] = []

    keywords = rules.get("keywords", [
        "confidential", "proprietary", "trade secret", "internal use only",
        "do not distribute", "restricted", "classified", "NDA", "non-disclosure"
    ])

    for page in pages:
        if page["is_empty"]:
            continue

        text = page["text"]
        page_num = page["page_number"]

        rules_json = json.dumps(rules)
        keywords_json = json.dumps(keywords)
        text_snippet = text[:3000]

        # Build check list dynamically from rules
        checks = [
            "- Documents marked confidential/restricted/proprietary",
            "- Internal company financial projections or unreleased data",
            "- Trade secrets or proprietary methodologies",
        ]
        if rules.get("check_ip", True):
            checks.append("- Intellectual property descriptions (patents, algorithms)")
        checks.append("- Internal employee data or org structures")
        if rules.get("check_financial", True):
            checks.append("- Vendor contracts or pricing details")
        checks.append("- Unreleased product roadmaps or feature specs")

        checks_str = "\n".join(checks)

        prompt = (
            "You are a corporate information security analyst. "
            "Analyze this text for confidential or proprietary business information.\n\n"
            f"COMPLIANCE RULES: {rules_json}\n"
            f"KNOWN CONFIDENTIAL KEYWORDS: {keywords_json}\n\n"
            f"TASK: Flag any of the following if found:\n{checks_str}\n\n"
            f"TEXT (Page {page_num}):\n\"\"\"\n{text_snippet}\n\"\"\"\n\n"
            "Respond ONLY in this JSON format:\n"
            "{\n"
            '  "has_confidential": true/false,\n'
            '  "findings": [\n'
            "    {\n"
            '      "severity": "HIGH/MEDIUM/LOW",\n'
            '      "category": "financial/IP/employee_data/trade_secret/contract/other",\n'
            '      "description": "what was found",\n'
            '      "evidence": "relevant excerpt (max 100 chars)"\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Always return valid JSON. If nothing found, return has_confidential: false with empty findings array."
        )

        response = call_groq_confidential(prompt)

        if response.startswith("ERROR:"):
            findings.append(Finding(
                page_number=page_num,
                check_type="CONFIDENTIAL",
                severity="LOW",
                description=f"Groq API Error: {response[:100]}",
                evidence="AI analysis failed - check API key",
                flagged=True
            ))
            continue

        try:
            # Fix: normalise whitespace + repair truncated JSON before parsing
            clean = response.strip().replace("```json", "").replace("```", "")
            clean = clean.replace('\n', ' ').replace('\r', '')
            if clean.count('{') > clean.count('}'):
                clean += '}'
            if clean.count('[') > clean.count(']'):
                clean += ']}'

            result = json.loads(clean)

            if result.get("has_confidential"):
                for f in result.get("findings", []):
                    findings.append(Finding(
                        page_number=page_num,
                        check_type="CONFIDENTIAL",
                        severity=f.get("severity", "HIGH"),
                        description=f.get("description", "Confidential content detected"),
                        evidence=f.get("evidence", ""),
                        flagged=True
                    ))

        except (json.JSONDecodeError, KeyError) as e:
            # Surface parse failures as visible findings instead of silent pass
            findings.append(Finding(
                page_number=page_num,
                check_type="CONFIDENTIAL",
                severity="MEDIUM",
                description=f"[AI] Parse error on confidential check: {str(e)[:80]}",
                evidence=f"Raw response: {response[:150]}",
                flagged=True
            ))

    state["confidential_findings"] = findings
    return state