import streamlit as st
import os
import json
import tempfile
from datetime import datetime
from pipeline.extractor import extract_pages, get_pdf_metadata
from pipeline.graph import build_compliance_graph
from pipeline.state import ComplianceState
from pipeline.report_generator import generate_report

st.set_page_config(
    page_title="PDF Compliance Scanner",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .metric-card {
        background: linear-gradient(135deg, #1A1A2E 0%, #16213E 100%);
        border: 1px solid #0F3460;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        margin: 5px;
    }
    .finding-high { border-left: 4px solid #FF4444; padding: 10px; margin: 5px 0; }
    .finding-medium { border-left: 4px solid #FF8800; padding: 10px; margin: 5px 0; }
    .finding-low { border-left: 4px solid #FFCC00; padding: 10px; margin: 5px 0; }
    .status-pass { color: #28A745; font-weight: bold; font-size: 1.5em; }
    .status-fail { color: #DC3545; font-weight: bold; font-size: 1.5em; }
    .status-review { color: #FFC107; font-weight: bold; font-size: 1.5em; }
</style>
""", unsafe_allow_html=True)


def load_rules(path="rules/default_rules.json") -> dict:
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return get_default_rules()


def get_default_rules() -> dict:
    return {
        "pii": {
            "check_emails": True,
            "check_phones": True,
            "check_ssn": True,
            "check_names": True
        },
        "confidential": {
            "keywords": ["confidential", "proprietary", "internal use only",
                         "do not distribute", "trade secret", "restricted"],
            "check_financial": True,
            "check_ip": True
        },
        "encoding": {
            "required_encoding": "utf-8",
            "allowed_languages": ["en"],
            "max_non_printable": 10
        },
        "abusive": {
            "check_hate_speech": True,
            "check_threats": True,
            "check_explicit": True,
            "check_illegal": True
        }
    }


if "rules" not in st.session_state:
    st.session_state.rules = load_rules()
if "scan_result" not in st.session_state:
    st.session_state.scan_result = None
if "report_path" not in st.session_state:
    st.session_state.report_path = None


with st.sidebar:
    st.title("⚙️ Compliance Rules")
    st.markdown("---")

    tab_pii, tab_conf, tab_enc, tab_abuse = st.tabs(["PII", "Confid.", "Encoding", "Abusive"])

    with tab_pii:
        st.subheader("PII Settings")
        rules = st.session_state.rules
        rules["pii"]["check_emails"] = st.checkbox("Check Emails", value=rules["pii"]["check_emails"])
        rules["pii"]["check_phones"] = st.checkbox("Check Phone Numbers", value=rules["pii"]["check_phones"])
        rules["pii"]["check_ssn"] = st.checkbox("Check SSN", value=rules["pii"]["check_ssn"])
        rules["pii"]["check_names"] = st.checkbox("Check Full Names", value=rules["pii"]["check_names"])
        

    with tab_conf:
        st.subheader("Confidential Keywords")
        kw_text = st.text_area("One keyword per line",
            value="\n".join(rules["confidential"]["keywords"]), height=150)
        rules["confidential"]["keywords"] = [k.strip() for k in kw_text.split("\n") if k.strip()]
        rules["confidential"]["check_financial"] = st.checkbox("Check Financial Data",
            value=rules["confidential"]["check_financial"])
        rules["confidential"]["check_ip"] = st.checkbox("Check Intellectual Property",
            value=rules["confidential"]["check_ip"])

    with tab_enc:
        st.subheader("Encoding Rules")
        rules["encoding"]["required_encoding"] = st.selectbox(
            "Required Encoding", ["utf-8", "ascii"], index=0)
        lang_options = ["en", "fr", "de", "es", "zh", "ja"]
        rules["encoding"]["allowed_languages"] = st.multiselect(
            "Allowed Languages", lang_options,
            default=rules["encoding"]["allowed_languages"])

    with tab_abuse:
        st.subheader("Abusive Content")
        rules["abusive"]["check_hate_speech"] = st.checkbox("Hate Speech",
            value=rules["abusive"]["check_hate_speech"])
        rules["abusive"]["check_threats"] = st.checkbox("Threats/Violence",
            value=rules["abusive"]["check_threats"])
        rules["abusive"]["check_explicit"] = st.checkbox("Explicit Content",
            value=rules["abusive"]["check_explicit"])
        rules["abusive"]["check_illegal"] = st.checkbox("Illegal Instructions",
            value=rules["abusive"]["check_illegal"])

    st.markdown("---")
    if st.button("💾 Save Rules", use_container_width=True):
        os.makedirs("rules", exist_ok=True)
        with open("rules/default_rules.json", "w") as f:
            json.dump(rules, f, indent=2)
        st.success("Rules saved!")

    if st.button("🔄 Reset to Defaults", use_container_width=True):
        st.session_state.rules = get_default_rules()
        st.rerun()


st.title("📋 PDF Compliance Scanner")
st.markdown("*Powered by Groq LLaMA 3 + LangGraph*")
st.markdown("---")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📤 Upload PDF")
    uploaded_file = st.file_uploader(
        "Drop your PDF here",
        type=["pdf"],
        help="Text-based PDFs only. Scanned image PDFs are not supported."
    )

    if uploaded_file:
        st.info(f"📄 **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")

        if st.button("🚀 Run Compliance Scan", type="primary", use_container_width=True):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name

            with st.spinner("🔍 Extracting pages..."):
                pages = extract_pages(tmp_path)
                metadata = get_pdf_metadata(tmp_path)

            st.success(f"✅ Extracted {len(pages)} pages")

            initial_state = ComplianceState(
                pdf_path=tmp_path,
                pdf_name=uploaded_file.name,
                pages=pages,
                rules=st.session_state.rules,
                pii_findings=[],
                confidential_findings=[],
                encoding_findings=[],
                abusive_findings=[],
                all_findings=[],
                summary={},
                report_path=None,
                error=None,
            )

            progress_bar = st.progress(0, text="Running LangGraph pipeline...")
            graph = build_compliance_graph()

            progress_bar.progress(25, text="🔐 PII Agent running...")
            progress_bar.progress(50, text="🔒 Confidential Agent running...")
            progress_bar.progress(75, text="🔤 Encoding + Abusive Agents running...")

            final_state = graph.invoke(initial_state)

            progress_bar.progress(90, text="📊 Generating report...")
            report_path = generate_report(final_state)
            final_state["report_path"] = report_path

            progress_bar.progress(100, text="✅ Done!")
            st.session_state.scan_result = final_state
            st.session_state.report_path = report_path
            st.rerun()

with col2:
    st.subheader("ℹ️ How It Works")
    st.markdown("""
    1. **Upload** any text-based PDF
    2. **LangGraph** orchestrates 4 AI agents:
       - 🔐 PII Detection (Groq + Regex)
       - 🔒 Confidential Info (Groq)
       - 🔤 Encoding Check (Deterministic)
       - ⚠️ Abusive Content (Groq)
    3. **Get** a page-wise compliance report
    4. **Download** PDF or JSON report
    5. **Edit** rules in the sidebar anytime
    """)


if st.session_state.scan_result:
    result = st.session_state.scan_result
    summary = result["summary"]
    st.markdown("---")
    st.subheader("📊 Scan Results")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Compliance Score", f"{summary['compliance_score']}/100")
    m2.metric("Total Pages", summary["total_pages"])
    m3.metric("Flagged Pages", len(summary["flagged_pages"]))
    m4.metric("Total Issues", summary["total_findings"])
    status = summary["overall_status"]
    m5.metric("Status", status)

    st.markdown("---")

    by_type = summary["findings_by_type"]
    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("PII Issues", by_type.get("PII", 0), delta_color="inverse")
    col_b.metric("Confidential Issues", by_type.get("CONFIDENTIAL", 0), delta_color="inverse")
    col_c.metric("Encoding Issues", by_type.get("ENCODING", 0), delta_color="inverse")
    col_d.metric("Abusive Issues", by_type.get("ABUSIVE", 0), delta_color="inverse")

    if result["all_findings"]:
        st.subheader("🔎 Detailed Findings")
        import pandas as pd
        df = pd.DataFrame(result["all_findings"])
        df = df[["page_number", "check_type", "severity", "description", "evidence"]]
        df.columns = ["Page", "Check Type", "Severity", "Description", "Evidence"]

        def color_severity(val):
            colors = {"HIGH": "background-color: #FF4444; color: white",
                      "MEDIUM": "background-color: #FF8800; color: white",
                      "LOW": "background-color: #FFCC00"}
            return colors.get(val, "")

        st.dataframe(
            df.style.map(color_severity, subset=["Severity"]),
            use_container_width=True,
            height=400
        )
    else:
        st.success("🎉 No compliance violations found! The document is clean.")

    st.markdown("---")
    st.subheader("📥 Download Report")
    dl1, dl2 = st.columns(2)

    with dl1:
        if os.path.exists(st.session_state.report_path):
            with open(st.session_state.report_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download PDF Report",
                    data=f.read(),
                    file_name=os.path.basename(st.session_state.report_path),
                    mime="application/pdf",
                    use_container_width=True
                )

    with dl2:
        json_path = st.session_state.report_path.replace(".pdf", ".json")
        if os.path.exists(json_path):
            with open(json_path) as f:
                st.download_button(
                    label="⬇️ Download JSON Report",
                    data=f.read(),
                    file_name=os.path.basename(json_path),
                    mime="application/json",
                    use_container_width=True
                )
