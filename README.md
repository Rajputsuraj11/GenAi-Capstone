# 📋 PDF Compliance Scanner

AI-powered PDF compliance pipeline using Groq, LangGraph, and Streamlit.

## Features

- 🔐 **PII Detection** (emails, phones, SSNs, names)
- 🔒 **Confidential Information** flagging
- 🔤 **Encoding Consistency** checks (UTF-8, English only)
- ⚠️ **Abusive/Unlawful Content** detection
- 📊 **Page-wise compliance** reports (PDF + JSON)
- ⚙️ **Editable compliance rules** via UI

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     STREAMLIT UI                            │
│  [Upload PDF]  [Edit Rules]  [View Report]  [Download]      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              PDF INGESTION LAYER (PyMuPDF)                  │
│   Extract text per page → Detect encoding → Chunk pages     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  LANGGRAPH PIPELINE                         │
│                                                             │
│  [State: PageChunks + Rules + Findings]                     │
│                                                             │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐     │
│  │  PII    │──▶│Confid.  │──▶│Encoding │──▶│Abusive  │     │
│  │ Agent   │   │ Agent   │   │ Agent   │   │ Agent   │     │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘     │
│                                                    │        │
│                                                    ▼        │
│                                          [Aggregator Node]  │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                 REPORT GENERATOR                            │
│         JSON findings → Formatted PDF/HTML report           │
└─────────────────────────────────────────────────────────────┘
```

## Setup

```bash
git clone https://github.com/Rajputsuraj11/GenAi-Capstone.git
cd GenAi-Capstone
pip install -r requirements.txt
cp .env.example .env  # Add your Groq API key
streamlit run app.py
```

## Requirements

- Python 3.10+
- Groq API Key (free tier available)
  - Get your key at: https://console.groq.com

## Usage

1. Run the Streamlit app: `streamlit run app.py`
2. Upload any text-based PDF
3. Edit compliance rules in the sidebar if needed
4. Click "Run Compliance Scan"
5. View results and download reports

## Project Structure

```
pdf-compliance-scanner/
├── app.py                          # Streamlit entry point
├── requirements.txt
├── .env                            # API key (not committed)
├── .env.example                    # API key template
├── .gitignore
├── README.md
│
├── pipeline/
│   ├── __init__.py
│   ├── extractor.py                # PyMuPDF text extraction
│   ├── graph.py                    # LangGraph pipeline definition
│   ├── state.py                    # Shared state schema
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── pii_agent.py            # PII detection agent
│   │   ├── confidential_agent.py   # Confidential info agent
│   │   ├── encoding_agent.py       # Encoding consistency agent
│   │   ├── abusive_agent.py        # Abusive content agent
│   │   └── aggregator.py           # Results aggregator node
│   └── report_generator.py         # Report builder
│
├── rules/
│   └── default_rules.json          # Default compliance rules
│
├── reports/                        # Auto-generated reports
│
├── sample_pdfs/                    # Test PDFs
│
└── scripts/
    └── create_test_pdf.py          # Generate test PDF
```

## Compliance Checks

| Check | Description | Method |
|-------|-------------|--------|
| PII | Emails, phones, SSNs, addresses | Regex + Groq |
| Confidential | Trade secrets, internal data | Groq |
| Encoding | UTF-8, English only | Deterministic |
| Abusive | Hate speech, illegal content | Groq |

## Technologies

- **LangGraph**: Agent orchestration
- **Groq**: AI analysis (fast LLM inference)
- **PyMuPDF**: PDF text extraction
- **Streamlit**: Web UI
- **ReportLab**: PDF report generation

## License

MIT License

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.
