import json
from typing import List
from pipeline.state import ComplianceState, Finding
from pipeline.nodes import call_gemini


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
        prompt = ("You are a corporate information security analyst. Analyze this text for confidential or proprietary business information.\n\n"
                  + "COMPLIANCE RULES: " + rules_json + "\n"
                  + "KNOWN CONFIDENTIAL KEYWORDS: " + keywords_json + "\n\n"
                  + "TASK: Flag any of the following if found:\n"
                  + "- Documents marked confidential/restricted/proprietary\n"
                  + "- Internal company financial projections or unreleased data\n"
                  + "- Trade secrets or proprietary methodologies\n"
                  + "- Intellectual property descriptions (patents, algorithms)\n"
                  + "- Internal employee data or org structures\n"
                  + "- Vendor contracts or pricing details\n"
                  + "- Unreleased product roadmaps or feature specs\n\n"
                  + "TEXT (Page " + str(page_num) + "):\n\"\"\"\n" + text_snippet
                  + "\"\"\"\n\n"
                  + "Respond ONLY in this JSON format:\n"
                  + '{\n  "has_confidential": true/false,\n  "findings": [\n    {\n      "severity": "HIGH/MEDIUM/LOW",\n      "category": "financial/IP/employee_data/trade_secret/contract/other",\n      "description": "what was found",\n      "evidence": "relevant excerpt (max 100 chars)"\n    }\n  ]\n}')
        response = call_gemini(prompt)

        try:
            clean = response.strip().replace("```json", "").replace("```", "")
            result = json.loads(clean)

            if result.get("has_confidential"):
                for f in result.get("findings", []):
                    findings.append(Finding(
                        page_number=page_num,
                        check_type="CONFIDENTIAL",
                        severity=f.get("severity", "HIGH"),
                        description=f.get("description", ""),
                        evidence=f.get("evidence", ""),
                        flagged=True
                    ))
        except (json.JSONDecodeError, KeyError):
            pass

    state["confidential_findings"] = findings
    return state
