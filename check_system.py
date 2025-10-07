"""
RegDelta System Check
Verify installation and dependencies
"""

import sys
from pathlib import Path


def check_python_version():
    """Check Python version"""
    print("Checking Python version...")
    version = sys.version_info
    if version >= (3, 10):
        print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor}.{version.micro} (requires 3.10+)")
        return False


def check_dependencies():
    """Check required packages"""
    print("\nChecking dependencies...")
    
    required = {
        'yaml': 'pyyaml',
        'pandas': 'pandas',
        'numpy': 'numpy',
        'streamlit': 'streamlit',
        'sentence_transformers': 'sentence-transformers',
        'faiss': 'faiss-cpu',
        'rapidfuzz': 'rapidfuzz'
    }
    
    optional = {
        'fitz': 'PyMuPDF',
        'pdfplumber': 'pdfplumber'
    }
    
    all_ok = True
    
    # Check required
    for module, package in required.items():
        try:
            __import__(module)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} (REQUIRED)")
            all_ok = False
    
    # Check optional
    pdf_extractors = []
    for module, package in optional.items():
        try:
            __import__(module)
            print(f"✓ {package}")
            pdf_extractors.append(package)
        except ImportError:
            print(f"⚠ {package} (optional)")
    
    if not pdf_extractors:
        print("\n⚠ WARNING: No PDF extractors available. Install at least one:")
        print("  pip install PyMuPDF")
        print("  pip install pdfplumber")
        all_ok = False
    
    return all_ok


def check_files():
    """Check required files exist"""
    print("\nChecking configuration files...")
    
    required_files = [
        'config.yml',
        'lexicon.yml',
        'catalogs/pci.yml',
        'catalogs/rbi_demo.yml'
    ]
    
    all_ok = True
    
    for file in required_files:
        path = Path(file)
        if path.exists():
            print(f"✓ {file}")
        else:
            print(f"✗ {file} (MISSING)")
            all_ok = False
    
    return all_ok


def check_directories():
    """Check/create required directories"""
    print("\nChecking directories...")
    
    required_dirs = [
        'data',
        'audit',
        'logs',
        'scenarios'
    ]
    
    for dir_name in required_dirs:
        path = Path(dir_name)
        if path.exists():
            print(f"✓ {dir_name}/")
        else:
            path.mkdir(parents=True, exist_ok=True)
            print(f"✓ {dir_name}/ (created)")
    
    return True


def test_imports():
    """Test critical imports"""
    print("\nTesting critical imports...")
    
    # Add project root to Python path
    project_root = Path(__file__).parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    try:
        from utils.config import get_config
        print("✓ utils.config")
    except Exception as e:
        print(f"✗ utils.config: {e}")
        return False
    
    try:
        from utils.audit import get_audit_logger
        print("✓ utils.audit")
    except Exception as e:
        print(f"✗ utils.audit: {e}")
        return False
    
    try:
        from agents.extractor import ExtractorAgent
        print("✓ agents.extractor")
    except Exception as e:
        print(f"✗ agents.extractor: {e}")
        return False
    
    try:
        from agents.mapper import MapperAgent
        print("✓ agents.mapper")
    except Exception as e:
        print(f"✗ agents.mapper: {e}")
        return False
    
    try:
        from agents.planner import PlannerAgent
        print("✓ agents.planner")
    except Exception as e:
        print(f"✗ agents.planner: {e}")
        return False
    
    return True


def main():
    print("=" * 60)
    print("RegDelta System Check")
    print("=" * 60)
    
    checks = {
        'Python Version': check_python_version(),
        'Dependencies': check_dependencies(),
        'Configuration Files': check_files(),
        'Directories': check_directories(),
        'Module Imports': test_imports()
    }
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for name, result in checks.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{name}: {status}")
    
    if all(checks.values()):
        print("\n✓ All checks passed! RegDelta is ready to use.")
        print("\nNext steps:")
        print("  1. Run UI: streamlit run ui/app.py")
        print("  2. Or CLI: python run.py --new your-pdf.pdf")
        print("  3. See QUICKSTART.md for more info")
        return 0
    else:
        print("\n✗ Some checks failed. Please fix the issues above.")
        print("\nTo install missing dependencies:")
        print("  pip install -r requirements.txt")
        return 1


if __name__ == "__main__":
    sys.exit(main())
