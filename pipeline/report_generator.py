import json
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, red, green, orange, black, white
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from pipeline.state import ComplianceState


SEVERITY_COLORS = {
    "HIGH":   HexColor("#FF4444"),
    "MEDIUM": HexColor("#FF8800"),
    "LOW":    HexColor("#FFCC00"),
}

STATUS_COLORS = {
    "PASS":   HexColor("#28A745"),
    "REVIEW": HexColor("#FFC107"),
    "FAIL":   HexColor("#DC3545"),
}


def generate_report(state: ComplianceState, output_dir: str = "reports") -> str:
    """Generate a formatted PDF compliance report."""
    os.makedirs(output_dir, exist_ok=True)
    summary = state["summary"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/compliance_report_{timestamp}.pdf"

    doc = SimpleDocTemplate(filename, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle("title", fontSize=22, fontName="Helvetica-Bold",
                                  textColor=HexColor("#1A1A2E"), alignment=TA_CENTER)
    story.append(Paragraph("PDF Compliance Scan Report", title_style))
    story.append(Spacer(1, 0.2*inch))

    status = summary["overall_status"]
    status_color = STATUS_COLORS.get(status, HexColor("#6C757D"))
    score = summary["compliance_score"]

    banner_data = [
        ["PDF File", summary["pdf_name"], "Status", status],
        ["Scan Date", summary["scan_timestamp"][:10], "Compliance Score", f"{score}/100"],
        ["Total Pages", str(summary["total_pages"]),
         "Flagged Pages", str(len(summary["flagged_pages"]))],
    ]
    banner_table = Table(banner_data, colWidths=[1.5*inch, 2.5*inch, 1.5*inch, 1.5*inch])
    banner_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), HexColor("#E8F4FD")),
        ("BACKGROUND", (2, 0), (2, -1), HexColor("#E8F4FD")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [white, HexColor("#F8F9FA")]),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (3, 0), (3, 0), status_color),
        ("TEXTCOLOR", (3, 0), (3, 0), white),
        ("FONTNAME", (3, 0), (3, 0), "Helvetica-Bold"),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 0.3*inch))

    story.append(Paragraph("Findings Summary by Check Type", styles["Heading2"]))
    story.append(Spacer(1, 0.1*inch))

    by_type = summary["findings_by_type"]
    check_labels = {
        "PII": "PII / Personal Data",
        "CONFIDENTIAL": "Confidential Information",
        "ENCODING": "Encoding Consistency",
        "ABUSIVE": "Abusive / Unlawful Content",
    }
    type_data = [["Check Type", "Findings", "Status"]]
    for key, label in check_labels.items():
        count = by_type.get(key, 0)
        row_status = "PASS" if count == 0 else f"{count} issue(s)"
        type_data.append([label, str(count), row_status])

    type_table = Table(type_data, colWidths=[3*inch, 1.5*inch, 2*inch])
    type_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1A1A2E")),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS", (1, 0), (-1, -1), [white, HexColor("#F8F9FA")]),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(type_table)
    story.append(Spacer(1, 0.3*inch))

    story.append(Paragraph("Detailed Page-wise Findings", styles["Heading2"]))
    story.append(Spacer(1, 0.1*inch))

    all_findings = state["all_findings"]
    if not all_findings:
        story.append(Paragraph("No compliance violations found. Document is clean.", styles["Normal"]))
    else:
        for finding in all_findings:
            sev = finding["severity"]
            sev_color = SEVERITY_COLORS.get(sev, HexColor("#AAAAAA"))
            finding_data = [
                [f"Page {finding['page_number']}", f"[{sev}]", finding["check_type"]],
                [finding["description"], "", ""],
                [f"Evidence: {finding['evidence'][:120]}", "", ""],
            ]
            f_table = Table(finding_data, colWidths=[1*inch, 0.8*inch, 4.7*inch])
            f_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, 0), HexColor("#1A1A2E")),
                ("TEXTCOLOR", (0, 0), (0, 0), white),
                ("BACKGROUND", (1, 0), (1, 0), sev_color),
                ("TEXTCOLOR", (1, 0), (1, 0), white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 2), (-1, 2), 8),
                ("TEXTCOLOR", (0, 2), (-1, 2), HexColor("#555555")),
                ("SPAN", (0, 1), (-1, 1)),
                ("SPAN", (0, 2), (-1, 2)),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#DDDDDD")),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#FFF9F0")]),
            ]))
            story.append(KeepTogether([f_table, Spacer(1, 0.1*inch)]))

    story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#CCCCCC")))
    story.append(Spacer(1, 0.1*inch))
    footer_style = ParagraphStyle("footer", fontSize=8, textColor=HexColor("#888888"), alignment=TA_CENTER)
    story.append(Paragraph(
        f"Generated by PDF Compliance Scanner | Powered by Google Gemini 1.5 Flash & LangGraph | {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        footer_style
    ))

    doc.build(story)

    json_path = filename.replace(".pdf", ".json")
    with open(json_path, "w") as f:
        json.dump({"summary": summary, "findings": state["all_findings"]}, f, indent=2, default=str)

    state["report_path"] = filename
    return filename
