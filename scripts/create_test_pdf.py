from reportlab.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import os


def create_test_pdf(output_path="sample_pdfs/test_compliance.pdf"):
    """Create a test PDF with sample PII and confidential content."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()

    content = [
        Paragraph("CONFIDENTIAL - INTERNAL USE ONLY", styles["Title"]),
        Spacer(1, 12),
        Paragraph("Employee Report - Q4 2024", styles["Heading1"]),
        Spacer(1, 12),
        Paragraph("Contact: john.doe@company.com | Phone: +1-555-123-4567", styles["Normal"]),
        Paragraph("SSN: 123-45-6789 | Address: 123 Main St, Springfield", styles["Normal"]),
        Spacer(1, 12),
        Paragraph("This document contains proprietary trade secrets and confidential business information.", styles["Normal"]),
        Paragraph("Do not distribute outside the organization.", styles["Normal"]),
        Spacer(1, 12),
        Paragraph("Financial Projections:", styles["Heading2"]),
        Paragraph("Q4 Revenue: $5.2M | Projected Q1 2025: $6.8M", styles["Normal"]),
        Paragraph("Unreleased Product: Project Alpha launching March 2025", styles["Normal"]),
    ]

    doc.build(content)
    print(f"Test PDF created at: {output_path}")
    return output_path


if __name__ == "__main__":
    create_test_pdf()
