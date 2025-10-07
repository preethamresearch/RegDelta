# RegDelta Installation Guide

## Prerequisites

- **Python**: 3.10 or higher
- **OS**: Windows, macOS, or Linux
- **Memory**: 4GB RAM minimum (8GB recommended)
- **Storage**: ~500MB for dependencies and models

---

## Step-by-Step Installation

### 1. Open PowerShell/Terminal

Navigate to the RegDelta directory:

```powershell
cd C:\Users\91861\OneDrive\Desktop\hackathon\RegDelta
```

### 2. Create Virtual Environment

```powershell
python -m venv venv
```

This creates an isolated Python environment.

### 3. Activate Virtual Environment

**Windows PowerShell:**

```powershell
.\venv\Scripts\Activate.ps1
```

**Windows CMD:**

```cmd
.\venv\Scripts\activate.bat
```

**macOS/Linux:**

```bash
source venv/bin/activate
```

You should see `(venv)` in your prompt.

### 4. Upgrade pip (recommended)

```powershell
python -m pip install --upgrade pip
```

### 5. Install Dependencies

```powershell
pip install -r requirements.txt
```

This will install:

- PyYAML (config)
- Pandas (data handling)
- NumPy (numerical operations)
- PyMuPDF (PDF extraction)
- pdfplumber (PDF fallback)
- sentence-transformers (embeddings)
- faiss-cpu (vector search)
- rapidfuzz (fuzzy matching)
- streamlit (web UI)

**Note**: First installation will take 3-5 minutes. The sentence-transformers library will download a model (~80MB) on first use.

### 6. Verify Installation

```powershell
python check_system.py
```

This checks:

- ✓ Python version
- ✓ All dependencies installed
- ✓ Configuration files present
- ✓ Directories created
- ✓ Module imports working

Expected output:

```
✓ All checks passed! RegDelta is ready to use.
```

---

## Troubleshooting

### Issue: PyMuPDF Installation Fails

**Solution 1**: Try installing just pdfplumber

```powershell
pip install pdfplumber
```

**Solution 2**: Use pre-built wheels

```powershell
pip install --upgrade pip wheel
pip install PyMuPDF
```

### Issue: "Execution policies" error on Windows

**Solution**: Allow script execution

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then try activating venv again.

### Issue: Streamlit won't start

**Check port 8501 availability:**

```powershell
netstat -ano | findstr :8501
```

**Use different port:**

```powershell
streamlit run ui/app.py --server.port 8502
```

### Issue: "Module not found" errors

**Ensure venv is activated:**

```powershell
# You should see (venv) in your prompt
# If not, activate again:
.\venv\Scripts\Activate.ps1
```

**Reinstall dependencies:**

```powershell
pip install -r requirements.txt --force-reinstall
```

### Issue: Out of memory during model loading

**Solution**: Close other applications and try again. The model requires ~500MB RAM.

---

## First Run

### Option 1: Web UI

```powershell
streamlit run ui/app.py
```

Browser opens at `http://localhost:8501`

### Option 2: Command Line

```powershell
python run.py --new sample.pdf --scenario test-run
```

---

## Verify Everything Works

1. **Run system check:**

   ```powershell
   python check_system.py
   ```

2. **Start UI:**

   ```powershell
   streamlit run ui/app.py
   ```

3. **Upload a test PDF** through the UI

4. **Click "Run Full Analysis"**

5. **Check results** in the tabs

---

## Next Steps

- Read `QUICKSTART.md` for usage guide
- Review `README.md` for full documentation
- Check `config.yml` for customization options
- Explore `lexicon.yml` for obligation patterns

---

## Uninstallation

To remove RegDelta:

1. **Deactivate venv:**

   ```powershell
   deactivate
   ```

2. **Delete venv folder:**

   ```powershell
   Remove-Item -Recurse -Force venv
   ```

3. **Delete project folder** (optional)

---

## Getting Help

- **Check logs**: `logs/regdelta.log`
- **Run system check**: `python check_system.py`
- **Review documentation**: `README.md`
- **Open an issue** on GitHub

---

## System Requirements Summary

| Component | Minimum      | Recommended |
| --------- | ------------ | ----------- |
| Python    | 3.10         | 3.11+       |
| RAM       | 4GB          | 8GB         |
| Storage   | 500MB        | 1GB         |
| CPU       | 2 cores      | 4+ cores    |
| GPU       | Not required | Not used    |

---

**Installation complete!** 🎉

Ready to analyze compliance documents? See `QUICKSTART.md` for your first analysis.
