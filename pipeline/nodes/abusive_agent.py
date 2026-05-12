import json
from typing import List
from pipeline.state import ComplianceState, Finding
from pipeline.nodes import call_groq_abusive


def abusive_check_node(state: ComplianceState) -> ComplianceState:
    """
    Agent 4: Detect abusive, hateful, or unlawful content.
    """
    pages = state["pages"]
    rules = state["rules"].get("abusive", {})
    findings: List[Finding] = []

    for page in pages:
        if page["is_empty"]:
            continue

        text = page["text"]
        page_num = page["page_number"]

        rules_json = json.dumps(rules)
        text_snippet = text[:3000]
        prompt = ("You are a content moderation and legal compliance specialist. Analyze this text for any harmful or unlawful content.\n\n"
                  + "COMPLIANCE RULES: " + rules_json + "\n\n"
                  + "TASK: Check for the following violations:\n"
                  + "- Hate speech, slurs, or discriminatory language targeting any group\n"
                  + "- Explicit threats or incitement to violence\n"
                  + "- Sexually explicit or inappropriate content\n"
                  + "- Instructions for illegal activities (fraud, hacking, drug synthesis, etc.)\n"
                  + "- Harassment or cyberbullying content\n"
                  + "- Misinformation that could cause harm\n\n"
                  + "TEXT (Page " + str(page_num) + "):\n\"\"\"\n" + text_snippet
                  + "\"\"\"\n\n"
                  + "Respond ONLY in this JSON format:\n"
                  + '{\n  "has_violations": true/false,\n  "findings": [\n    {\n      "severity": "HIGH/MEDIUM/LOW",\n      "violation_type": "hate_speech/threat/explicit/illegal/harassment/misinformation/other",\n      "description": "description of the violation",\n      "evidence": "[REDACTED - violation detected]"\n    }\n  ]\n}\n\n'
                  + "IMPORTANT: Do NOT reproduce harmful content in your response. Use [REDACTED] for evidence.")
        response = call_groq_abusive(prompt)

        try:
            clean = response.strip().replace("```json", "").replace("```", "")
            result = json.loads(clean)

            if result.get("has_violations"):
                for f in result.get("findings", []):
                    findings.append(Finding(
                        page_number=page_num,
                        check_type="ABUSIVE",
                        severity=f.get("severity", "HIGH"),
                        description=f.get("description", ""),
                        evidence=f.get("evidence", "[REDACTED]"),
                        flagged=True
                    ))
        except (json.JSONDecodeError, KeyError):
            pass

    state["abusive_findings"] = findings
    return state
