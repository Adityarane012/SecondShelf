"""
verify_setup.py — SecondShelf Phase 0 validation script.
Run this after `pip install -r requirements.txt` to confirm everything works.

Usage:
    python verify_setup.py
"""

import sys
import os

def check_python_version():
    version = sys.version_info
    assert version >= (3, 10), f"Python 3.10+ required, found {version.major}.{version.minor}"
    print(f"  ✓ Python {version.major}.{version.minor}.{version.micro}")

def check_imports():
    packages = [
        ("groq", "groq"),
        ("sentence_transformers", "sentence-transformers"),
        ("sklearn", "scikit-learn"),
        ("numpy", "numpy"),
        ("frontmatter", "python-frontmatter"),
        ("dotenv", "python-dotenv"),
        ("streamlit", "streamlit"),
        ("requests", "requests"),
        ("bs4", "beautifulsoup4"),
    ]
    for module, package in packages:
        try:
            __import__(module)
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package}  ← run: pip install {package}")

def check_env():
    from dotenv import load_dotenv
    load_dotenv()
    key = os.getenv("GROQ_API_KEY", "")
    if not key or key == "gsk_...":
        print("  ✗ GROQ_API_KEY not set — edit your .env file")
        return False
    print(f"  ✓ GROQ_API_KEY found ({key[:8]}...)")
    return True

def check_groq_api(key):
    try:
        from groq import Groq
        client = Groq(api_key=key)
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": "Reply with the single word: OK"}],
            max_tokens=5,
        )
        reply = response.choices[0].message.content.strip()
        print(f"  ✓ Groq API responded: '{reply}'")
    except Exception as e:
        print(f"  ✗ Groq API call failed: {e}")

def check_folders():
    for folder in ["raw", "wiki", "static", "prompts"]:
        exists = os.path.isdir(folder)
        print(f"  {'✓' if exists else '✗'} {folder}/")

if __name__ == "__main__":
    print("\n─── SecondShelf — Phase 0 Environment Check ───\n")

    print("[ Python version ]")
    check_python_version()

    print("\n[ Package imports ]")
    check_imports()

    print("\n[ Folder structure ]")
    check_folders()

    print("\n[ Environment variables ]")
    key_ok = check_env()

    if key_ok:
        print("\n[ Groq API connectivity ]")
        from dotenv import load_dotenv
        load_dotenv()
        check_groq_api(os.getenv("GROQ_API_KEY"))

    print("\n─────────────────────────────────────────────\n")
    print("✅  Phase 0 complete if all items above show ✓")
    print("    Fix any ✗ items before moving to Phase 1.\n")
