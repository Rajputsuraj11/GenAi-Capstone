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

    for page in pages:
        if page["is_empty"]:
            continue

        text = page["text"]
        page_num = page["page_number"]
        local_findings = []

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

        rules_json = json.dumps(rules)
        text_snippet = text[:3000]
        prompt = ("You are a data privacy compliance officer. Analyze the following text from page "
                  + str(page_num) + " of a PDF.\n\n"
                  + "TASK: Identify any Personally Identifiable Information (PII) present.\n\n"
                  + "PII includes (per rules: " + rules_json + "):\n"
                  + "- Full names (especially if combined with other info)\n"
                  + "- Email addresses\n"
                  + "- Phone numbers\n"
                  + "- Physical addresses\n"
                  + "- Social Security Numbers / National IDs\n"
                  + "- Date of birth\n"
                  + "- Financial account numbers\n"
                  + "- Medical information\n\n"
                  + "TEXT TO ANALYZE:\n\"\"\"\n" + text_snippet
                  + "\"\"\"\n\n"
                  + "Respond in this EXACT JSON format only (no extra text):\n"
                  + '{\n  "has_pii": true/false,\n  "findings": [\n    {\n      "pii_type": "email/phone/name/address/ssn/other",\n      "severity": "HIGH/MEDIUM/LOW",\n      "description": "brief description",\n      "evidence": "masked evidence e.g. j***@example.com"\n    }\n  ]\n}')
        groq_response = call_groq_pii(prompt)

        gemini_found_pii = False

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
                # Try to fix common JSON issues before parsing
                clean = clean.replace('\n', ' ').replace('\r', '')
                # Handle incomplete JSON by adding missing braces/quotes if needed
                if clean.count('{') > clean.count('}'):
                    clean += '}'
                if clean.count('"') % 2 != 0:
                    clean += '"'
                
                result = json.loads(clean)

                if result.get("has_pii"):
                    gemini_found_pii = True
                    for f in result.get("findings", []):
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

        # Add regex findings, but avoid duplicates with AI findings
        regex_evidences = set()
        for ai_finding in findings:
            if isinstance(ai_finding, dict) and ai_finding.get('evidence') and "Pattern matches" not in ai_finding.get('evidence', ''):
                regex_evidences.add(ai_finding.get('evidence', '').lower())
        
        for rf in local_findings:
            regex_evidence = f"Pattern matches found: {str(rf['matches'])[:100]}"
            # Skip if AI already detected similar PII (avoid duplicates)
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
