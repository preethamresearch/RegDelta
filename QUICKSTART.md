# RegDelta - Quick Start Guide

## 🚀 Setup (5 minutes)

### Step 1: Install Dependencies

```powershell
# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1

# Install packages
pip install -r requirements.txt
```

**First-time note:** The first run will download the SentenceTransformer model (~80MB). This is cached locally.

---

## 🎯 Run RegDelta

### Option 1: Web UI (Recommended)

```powershell
streamlit run ui/app.py
```

Opens browser at `http://localhost:8501`

### Option 2: Command Line

```powershell
python run.py --new path/to/new_document.pdf --scenario my-test
```

With baseline:

```powershell
python run.py --baseline path/to/baseline.pdf --new path/to/new.pdf --scenario comparison-test
```

---

## 📝 Test with Sample

1. **Get a sample PDF** (any regulatory document)
2. **Upload via UI** or use CLI
3. **Wait for processing** (~1-2 minutes for 20-page doc)
4. **Review results** in the UI tabs

---

## 🔍 What Happens During Analysis

1. **Ingest** - Extracts text from PDF(s)
2. **Diff** - Compares baseline vs new (if both provided)
3. **Extract** - Finds obligations using lexicon rules
4. **Map** - Matches obligations to controls via embeddings
5. **Plan** - Generates actions and evidence schedules

---

## 📊 Understanding Results

### Obligations Tab

- Lists all detected requirements
- Color-coded by severity (High/Medium/Low)
- Shows modal phrases that triggered detection

### Mappings Tab

- Control matches for each obligation
- Scores: Blended (70% semantic + 30% lexical)
- Status: Accepted (>0.75), Review (0.60-0.75), Rejected (<0.60)

### Actions Tab

- Recommended action items
- Assigned owners from control catalog
- Due dates based on priority

### Exports Tab

- Download JSON/CSV reports
- Verify audit trail integrity

---

## ⚙️ Configuration Tips

### Adjust Mapping Thresholds

Edit `config.yml`:

```yaml
mapping:
  thresholds:
    high: 0.75 # Lower = more auto-accepts
    low: 0.60 # Lower = fewer review items
```

### Add Custom Controls

Create `catalogs/my-catalog.yml`:

```yaml
controls:
  - control_id: "MY-001"
    domain: "Security"
    title: "My custom control"
    description: "..."
    owner: "Security Team"
    evidence_examples:
      - "Example evidence"
```

Then update `config.yml`:

```yaml
controls:
  catalogs: ["pci.yml", "rbi_demo.yml", "my-catalog.yml"]
```

### Customize Lexicon

Edit `lexicon.yml` to add your own obligation patterns:

```yaml
modal_phrases:
  mandatory:
    - "is obligated to"
    - "has a duty to"
```

---

## 🐛 Common Issues

### "No obligations found"

- Check if your PDF has extractable text (not scanned image)
- Review lexicon.yml - add your domain-specific phrases
- Increase verbosity: Check `logs/regdelta.log`

### "Mapping scores too low"

- Your controls might not match the regulation domain
- Add/update control catalogs for better semantic matching
- Lower thresholds in config.yml

### "PDF extraction failed"

- Install pdfplumber: `pip install pdfplumber`
- Some PDFs need OCR (coming in Beta)

---

## 💡 Pro Tips

1. **Start with high-quality PDFs** (native text, not scans)
2. **Use meaningful scenario names** for easier tracking
3. **Review audit trail regularly** - `ui/app.py` → Exports tab
4. **Customize lexicon** for your regulatory domain
5. **Build domain-specific control catalogs** for better mapping

---

## 📚 Next Steps

- Read full `README.md` for detailed documentation
- Review `PRD.md` for product vision and roadmap
- Check `config.yml` for all configuration options
- Explore agent code in `agents/` for customization

---

**Need help?** Check logs at `logs/regdelta.log` or open an issue.

**Ready for production?** See roadmap in README for Alpha/Beta features.
