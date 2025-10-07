# RegDelta 📋

**Local-first Compliance Impact Analysis Tool**

<img width="1919" height="942" alt="image" src="https://github.com/user-attachments/assets/89a830f2-1cbc-4e7e-91f8-f16cdb54ab46" />


Turn incoming regulatory updates (RBI/SEBI/PCI/ISO/SOC2/GDPR) into reviewable impact plans in **< 30 minutes**, fully local with no external LLM/API calls.

---

## 🎯 Key Features

- ✅ **100% Local** - No external LLM or API calls, all processing on-device
- ✅ **Fast Analysis** - Complete impact assessment in under 30 minutes
- ✅ **Deterministic Extraction** - Rule-based obligation detection (no hallucinations)
- ✅ **Smart Mapping** - Local embeddings + FAISS for control matching
- ✅ **Tamper-Evident Audit** - SHA-256 hash chain for audit trail integrity
- ✅ **Dark Theme UI** - Professional Streamlit interface
- ✅ **Multi-Framework** - Supports PCI, RBI, SEBI, ISO, SOC2, GDPR and more

---

## 📦 Installation

### Prerequisites

- Python 3.10 or higher
- Windows/macOS/Linux

### Setup

```powershell
# Clone or navigate to the project directory
cd RegDelta

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Windows CMD:
# .\venv\Scripts\activate.bat

# macOS/Linux:
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 🚀 Quick Start

### 1. Start the Application

```powershell
streamlit run ui/app.py
```

The app will open in your default browser at `http://localhost:8501`

### 2. Fetch Sample Documents (Optional)

Download real regulatory documents for testing:

```powershell
python fetch_documents.py
```

This will download:

- **PCI DSS v4.0 → v4.0.1** (Payment Card Industry standards)
- **RBI KYC Master Direction → Nov 2024 Amendment** (Reserve Bank of India)
- **SEBI FPI Disclosures** (Securities and Exchange Board of India)

Documents are saved to `scenarios/` and ready to use.

### 3. Upload Documents

- **Baseline PDF** (optional): Previous version of the regulation
- **New PDF** (required): Latest regulatory update or circular

Or use the pre-fetched documents from `scenarios/`.

### 4. Run Analysis

Click **"🚀 Run Full Analysis"** and wait for processing:

1. **Ingest** - Extract text from PDFs
2. **Diff** - Compare baseline vs new (if baseline provided)
3. **Extract** - Identify obligations using lexicon rules
4. **Map** - Match obligations to existing controls
5. **Plan** - Generate actions and evidence schedules

### 5. Review Results

Navigate through tabs:

- **Obligations** - Extracted requirements with severity
- **Mappings** - Control matches with scores
- **Diff Summary** - Changes between versions
- **Actions** - Recommended action items
- **Exports** - Download JSON reports

---

## 📁 Project Structure

```
RegDelta/
├── agents/              # Agentic components
│   ├── extractor.py    # Obligation extraction
│   ├── mapper.py       # Control mapping
│   ├── planner.py      # Workflow orchestration
│   └── actions.py      # Action & evidence planning
├── utils/              # Utilities
│   ├── config.py       # Configuration loader
│   ├── audit.py        # Tamper-evident audit logger
│   ├── pdf_extractor.py # PDF text extraction
│   └── diff.py         # Document diffing
├── ui/                 # Streamlit UI
│   └── app.py          # Main application
├── catalogs/           # Control catalogs
│   ├── pci.yml         # PCI DSS controls
│   └── rbi_demo.yml    # RBI compliance controls
├── scenarios/          # Scenario data (uploaded PDFs)
├── data/               # Analysis outputs
├── audit/              # Audit trail logs
├── logs/               # Application logs
├── config.yml          # Main configuration
├── lexicon.yml         # Obligation detection rules
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

---

## ⚙️ Configuration

Edit `config.yml` to customize:

```yaml
storage:
  mode: json # json | sqlite (beta+)

controls:
  catalogs: ["pci.yml", "rbi_demo.yml"]

mapping:
  thresholds:
    high: 0.75 # Auto-accept threshold
    low: 0.60 # Review threshold

evidence:
  mode: "plan" # plan | dryrun | live

reviewer:
  identity: "prompt" # prompt | os
```

---

## 📊 Lexicon Customization

Modify `lexicon.yml` to add your own obligation patterns:

```yaml
modal_phrases:
  mandatory:
    - "must"
    - "shall"
    - "required to"

severity_keywords:
  high:
    - "prohibited"
    - "penalty"
    - "critical"
```

---

## 🗂️ Control Catalogs

Add your own control catalogs in `catalogs/`:

```yaml
controls:
  - control_id: "CTRL-001"
    domain: "Data Security"
    title: "Encrypt data at rest"
    description: "All sensitive data must be encrypted..."
    owner: "Security Team"
    evidence_examples:
      - "Encryption configuration files"
      - "Key management procedures"
```

---

## 🔒 Audit Trail

RegDelta maintains a tamper-evident audit trail:

- **SHA-256 hash chain** - Each entry linked to previous
- **Append-only log** - No modifications allowed
- **Verifiable** - Check integrity in UI or via API

Verify audit trail:

```python
from utils.audit import get_audit_logger

audit = get_audit_logger()
is_valid, line_num = audit.verify_chain()
```

---

## 📤 Exports

Export results as:

- **JSON** - Obligations, mappings, actions
- **CSV** - For Excel/spreadsheet analysis
- **JSONL** - Audit trail

---

## 🛠️ Development Roadmap

### PoC (Current) ✅

- ✅ PDF ingestion with fallback extractors
- ✅ Paragraph-level diffing
- ✅ Rule-based obligation extraction
- ✅ Local embedding + FAISS mapping
- ✅ Dark theme Streamlit UI
- ✅ JSON storage
- ✅ Audit hash chain

### Alpha (Week 2)

- [ ] Interactive review UI (accept/override/reject)
- [ ] SQLite storage option
- [ ] Enhanced action templates
- [ ] Webhook notifications (dry-run mode)

### Beta (Weeks 3-4)

- [ ] Multi-catalog control management
- [ ] Scenario comparison reports
- [ ] Golden-set metrics dashboard
- [ ] OCR fallback for scanned PDFs

### v1 (Month 2)

- [ ] Jira/GitHub issue integration
- [ ] Advanced catalog importers
- [ ] Role-based access (local auth)
- [ ] Batch processing

---

## 🧪 Testing

Test with sample PDFs:

1. Place baseline PDF in `scenarios/demo/baseline/`
2. Place new PDF in `scenarios/demo/new/`
3. Run analysis via UI

---

## 🐛 Troubleshooting

### PyMuPDF Installation Issues (Windows)

If PyMuPDF fails to install:

```powershell
# Try pdfplumber only
pip install pdfplumber
```

RegDelta will automatically use pdfplumber as fallback.

### Streamlit Port Already in Use

```powershell
streamlit run ui/app.py --server.port 8502
```

### Model Download Slow

First run downloads sentence-transformers model (~80MB). This is cached locally.

---

## License

[Apache License 2.0](LICENSE)

Copyright (c) 2025 RegDelta

Licensed under the Apache License, Version 2.0 (the "License");
**You may not use this file except in compliance with the License.**
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

---

## 📧 Support

For issues or questions:

- Open an issue on GitHub
- Check logs in `logs/regdelta.log`

---

## 🙏 Acknowledgments

- **SentenceTransformers** - Local embeddings
- **FAISS** - Efficient similarity search
- **Streamlit** - Web interface
- **PyMuPDF & pdfplumber** - PDF extraction

---

**Built for GRC teams who value privacy, speed, and auditability** 🚀
