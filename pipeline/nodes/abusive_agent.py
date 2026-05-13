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

        # Build check list dynamically from rules (mirrors pii_agent pattern)
        checks = []
        if rules.get("check_hate_speech", True):
            checks.append("- Hate speech, slurs, or discriminatory language targeting any group")
        if rules.get("check_threats", True):
            checks.append("- Explicit threats or incitement to violence")
        if rules.get("check_explicit", True):
            checks.append("- Sexually explicit or inappropriate content")
        if rules.get("check_illegal", True):
            checks.append("- Instructions for illegal activities (fraud, hacking, drug synthesis, etc.)")
        checks.append("- Harassment or cyberbullying content")
        checks.append("- Misinformation that could cause harm")

        checks_str = "\n".join(checks)

        prompt = (
            "You are a content moderation and legal compliance specialist. "
            "Analyze this text for any harmful or unlawful content.\n\n"
            f"COMPLIANCE RULES: {rules_json}\n\n"
            f"TASK: Check for the following violations:\n{checks_str}\n\n"
            f"TEXT (Page {page_num}):\n\"\"\"\n{text_snippet}\n\"\"\"\n\n"
            "Respond ONLY in this JSON format:\n"
            "{\n"
            '  "has_violations": true,\n'
            '  "findings": [\n'
            "    {\n"
            '      "severity": "HIGH/MEDIUM/LOW",\n'
            '      "violation_type": "hate_speech/threat/explicit/illegal/harassment/misinformation/other",\n'
            '      "description": "description of the violation",\n'
            '      "evidence": "[REDACTED - violation detected]"\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "IMPORTANT: Do NOT reproduce harmful content in your response. Use [REDACTED] for evidence.\n"
            "Even if there are no violations, always return valid JSON with has_violations: false and an empty findings array."
        )

        response = call_groq_abusive(prompt)

        # Bug 1 fix: was silently swallowing ALL errors with bare `pass`.
        # Now logs a finding so failures are visible instead of invisible.
        if response.startswith("ERROR:"):
            findings.append(Finding(
                page_number=page_num,
                check_type="ABUSIVE",
                severity="LOW",
                description=f"Groq API Error: {response[:100]}",
                evidence="AI analysis failed - check API key",
                flagged=True
            ))
            continue

        try:
            # Bug 2 fix: was not stripping markdown fences or normalising whitespace
            # before json.loads — multi-line LLM responses caused JSONDecodeError
            # which was silently swallowed, so findings were never written to state.
            clean = response.strip().replace("```json", "").replace("```", "")
            clean = clean.replace('\n', ' ').replace('\r', '')
            # Repair common truncation artefacts from max_tokens cutoff
            if clean.count('{') > clean.count('}'):
                clean += '}'
            if clean.count('[') > clean.count(']'):
                clean += ']}'

            result = json.loads(clean)

            if result.get("has_violations"):
                for f in result.get("findings", []):
                    findings.append(Finding(
                        page_number=page_num,
                        check_type="ABUSIVE",
                        severity=f.get("severity", "HIGH"),
                        description=f.get("description", "Abusive content detected"),
                        evidence=f.get("evidence", "[REDACTED]"),
                        flagged=True
                    ))
            # No violations on this page — intentionally add nothing

        except (json.JSONDecodeError, KeyError) as e:
            # Bug 3 fix: was `pass` — parse failures now surface as a visible finding
            findings.append(Finding(
                page_number=page_num,
                check_type="ABUSIVE",
                severity="MEDIUM",
                description=f"[AI] Parse error on abusive check: {str(e)[:80]}",
                evidence=f"Raw response: {response[:150]}",
                flagged=True
            ))

    state["abusive_findings"] = findings
    return state