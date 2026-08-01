"""
capture.py — SecondShelf Phase 1: The Archivist
================================================
One command to capture anything (note, URL, file) into raw/<uuid>.json.

Usage:
    python capture.py note "Your idea or thought here"
    python capture.py url "https://example.com"
    python capture.py file "/path/to/document.pdf"

Output schema (raw/YYYY-MM-DD_<uuid8>/):
    ├── meta.json
    │   {
    │       "id":        "<uuid4>",
    │       "timestamp": "<ISO-8601>",
    │       "type":      "note" | "url" | "file",
    │       "source":    "<original input>"
    │   }
    └── content.txt (or content.<ext>)
        <extracted text content>
"""

import uuid
import json
import argparse
import shutil
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

# Force UTF-8 output on Windows (avoids cp1252 emoji/Unicode errors)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ─── Constants ────────────────────────────────────────────────────────────────

RAW_DIR = Path(__file__).parent / "raw"
MAX_NOTE_CHARS = 8000      # Truncate before LLM classify (edge case E1-2)
MAX_FILE_BYTES = 50 * 1024 * 1024  # 50 MB — warn and skip copy (edge case E1-17)
URL_TIMEOUT = 10           # seconds (edge case E1-11)
MAX_REDIRECTS = 5          # (edge case E1-11)

# ─── Core Utilities ───────────────────────────────────────────────────────────

def generate_metadata() -> dict:
    """Generate a fresh UUID4 + ISO-8601 UTC timestamp, avoiding collisions."""
    while True:
        new_id = str(uuid.uuid4())
        dt = datetime.now(timezone.utc)
        folder = f"{dt.strftime('%Y-%m-%d')}_{new_id[:8]}"
        if not (RAW_DIR / folder).exists():  # edge case E1-20
            break
    return {"id": new_id, "timestamp": dt.isoformat(), "_folder": folder}


def save_capture(data: dict) -> Path:
    """Write a capture dict to raw/YYYY-MM-DD_<uuid8>/ atomically."""
    RAW_DIR.mkdir(exist_ok=True)
    folder = data.pop("_folder")
    out_path = RAW_DIR / folder
    
    # Atomic write: write to .tmp dir first, then rename (edge case E1-22)
    tmp_path = RAW_DIR / f".tmp_{data['id']}"
    tmp_path.mkdir(exist_ok=True)
    
    content = data.pop("content", "")
    raw_source = data.pop("raw_copy_source", None)
    
    with open(tmp_path / "meta.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    if data["type"] == "file" and data.get("copied_to_raw") and raw_source:
        ext = data.get("file_extension", "")
        shutil.copy2(raw_source, tmp_path / f"content{ext}")
    elif data["type"] in ("note", "url"):
        with open(tmp_path / "content.txt", "w", encoding="utf-8") as f:
            f.write(content)
            
    tmp_path.rename(out_path)
    return out_path


def file_hash(path: Path) -> str:
    """MD5 hash of file contents for duplicate detection (edge case E1-19)."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def existing_hashes() -> dict:
    """Return {md5_hash: uuid} for all captured files to detect duplicates."""
    hashes = {}
    for capture_file in RAW_DIR.glob("*/meta.json"):
        try:
            with open(capture_file, encoding="utf-8") as f:
                data = json.load(f)
            if data.get("type") == "file" and data.get("file_hash"):
                hashes[data["file_hash"]] = data["id"]
        except Exception:
            pass
    return hashes


def existing_urls() -> dict:
    """Return {url: uuid} for all captured URLs to detect duplicates (edge case E1-12)."""
    urls = {}
    for capture_file in RAW_DIR.glob("*/meta.json"):
        try:
            with open(capture_file, encoding="utf-8") as f:
                data = json.load(f)
            if data.get("type") == "url":
                urls[data.get("source", "")] = data["id"]
        except Exception:
            pass
    return urls



def migrate_legacy_json():
    """Migrate old flat JSON files to the new directory structure."""
    if not RAW_DIR.exists(): return
    for old_file in RAW_DIR.glob("*.json"):
        if old_file.name == "meta.json": continue
        try:
            with open(old_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Reconstruct the _folder param
            dt = data["timestamp"][:10]
            data["_folder"] = f"{dt}_{data['id'][:8]}"
            
            # If it was a file, we need to move the actual file into the folder
            if data.get("type") == "file" and data.get("raw_copy_path"):
                old_bin = Path(data["raw_copy_path"])
                if old_bin.exists():
                    data["raw_copy_source"] = str(old_bin)
                    
            save_capture(data)
            old_file.unlink()
            
            # Clean up the old binary file if it existed
            if data.get("type") == "file" and data.get("raw_copy_path"):
                old_bin = Path(data["raw_copy_path"])
                if old_bin.exists(): old_bin.unlink()
                
            print(f"  ℹ Migrated legacy capture: {old_file.name}")
        except Exception as e:
            print(f"  ⚠ Failed to migrate {old_file.name}: {e}")

# ─── Input Handlers ───────────────────────────────────────────────────────────

def handle_text(content: str, source: str = "cli") -> Path:
    """Capture a plain text note into raw/."""
    # Edge case E1-1 / E1-4: empty or whitespace-only content
    stripped = content.strip()
    if not stripped:
        print("Error: Note content cannot be empty or whitespace only.")
        sys.exit(1)

    # Edge case E1-2: truncate long content consistently.
    # ponytail: sidecar content_full dropped — classify/graph/ask only ever read
    # the JSON `content` field, so a separate overflow store would be silently
    # ignored downstream. Truncate once here; that's the single source of truth.
    if len(stripped) > MAX_NOTE_CHARS:
        print(f"  ! Note is very long ({len(stripped)} chars), truncating to {MAX_NOTE_CHARS}.")
        stripped = stripped[:MAX_NOTE_CHARS]

    meta = generate_metadata()
    data = {
        **meta,
        "type": "note",
        "source": source,
        "content": stripped,
    }
    path = save_capture(data)
    print(f"  ✓ Note captured  →  {path.name}")
    return path


def handle_url(url: str) -> Path:
    """Fetch a URL, extract title + text content, and capture it."""
    import requests
    from bs4 import BeautifulSoup

    # Edge case E1-6: malformed URL — auto-prepend https://
    parsed = urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
        print(f"  ℹ No scheme detected — using: {url}")
    elif parsed.scheme not in ("http", "https"):
        # Edge case CC-3-1: block file:// and other dangerous schemes
        print(f"Error: Only http/https URLs are supported. Got scheme: '{parsed.scheme}'")
        sys.exit(1)

    # Edge case E1-12: duplicate URL check
    dupes = existing_urls()
    if url in dupes:
        print(f"  ⚠ URL already captured (id: {dupes[url]}). Use --force to re-capture.")
        print(f"  Skipping.")
        sys.exit(0)

    title = ""
    content = ""
    fetch_failed = False
    js_required = False
    status_code = None

    try:
        session = requests.Session()
        session.max_redirects = MAX_REDIRECTS
        response = session.get(
            url,
            timeout=URL_TIMEOUT,
            allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (SecondShelf/1.0)"},
        )
        status_code = response.status_code

        # Edge case E1-8: non-200 status
        if response.status_code != 200:
            print(f"  ⚠ URL returned HTTP {response.status_code}. Storing URL only.")
            fetch_failed = True
        else:
            # Edge case E1-13: binary content (PDF, image, etc.)
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                print(f"  ⚠ Non-HTML content type: {content_type}. "
                      f"Storing URL only (consider using 'file' capture instead).")
                fetch_failed = True
            else:
                soup = BeautifulSoup(response.text, "html.parser")

                # Extract title
                title_tag = soup.find("title")
                title = title_tag.get_text(strip=True) if title_tag else ""

                # Edge case E1-9: JS-rendered SPA detection (empty body)
                body_text = soup.get_text(separator=" ", strip=True)
                if len(body_text) < 100:
                    print(f"  ⚠ Very little text found — page may require JavaScript rendering.")
                    js_required = True

                # Edge case E1-10: login/paywall detection
                login_hints = ["sign in", "log in", "login", "create account", "subscribe"]
                if any(hint in body_text.lower() for hint in login_hints) and len(body_text) < 500:
                    print(f"  ⚠ Page may be behind a login/paywall. Content may be incomplete.")

                # Strip HTML tags from content for clean text (edge case E5-6 / CC-3-3)
                # Remove script and style blocks first
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()
                content = soup.get_text(separator=" ", strip=True)
                content = " ".join(content.split())  # normalize whitespace
                content = content[:MAX_NOTE_CHARS]

    except requests.exceptions.TooManyRedirects:
        print(f"  ⚠ Too many redirects (>{MAX_REDIRECTS}). Storing URL only.")
        fetch_failed = True
    except requests.exceptions.ConnectionError:
        print(f"  ⚠ Could not connect to {url}. Storing URL only.")
        fetch_failed = True
    except requests.exceptions.Timeout:
        print(f"  ⚠ Request timed out after {URL_TIMEOUT}s. Storing URL only.")
        fetch_failed = True
    except Exception as e:
        print(f"  ⚠ Unexpected error fetching URL: {e}. Storing URL only.")
        fetch_failed = True

    meta = generate_metadata()
    data = {
        **meta,
        "type": "url",
        "source": url,
        "title": title,
        "content": content if not fetch_failed else "",
        "fetch_failed": fetch_failed,
        "js_required": js_required,
        **({"status_code": status_code} if status_code else {}),
    }
    path = save_capture(data)
    status_label = f"(title: '{title[:60]}')" if title else "(no title extracted)"
    print(f"  ✓ URL captured   →  {path.name}  {status_label}")
    return path


def handle_file(filepath: str) -> Path:
    """Copy or reference a file into raw/."""
    src = Path(filepath).expanduser().resolve()

    # Edge case E1-14: file doesn't exist
    if not src.exists():
        print(f"Error: File not found: {src}")
        sys.exit(1)

    # Edge case E1-15: path is a directory
    if src.is_dir():
        print(f"Error: '{src}' is a directory. Please specify a file path.")
        sys.exit(1)

    # Edge case E1-16: no read permission
    try:
        src.stat()
    except PermissionError:
        print(f"Error: No read permission for: {src}")
        sys.exit(1)

    # Edge case E1-19: duplicate file detection by MD5
    try:
        src_hash = file_hash(src)
        dupes = existing_hashes()
        if src_hash in dupes:
            print(f"  ⚠ This file has already been captured (id: {dupes[src_hash]}).")
            print(f"  Skipping duplicate.")
            sys.exit(0)
    except Exception:
        src_hash = None  # hash failed — proceed anyway

    # Edge case E1-17: very large file — store reference only
    file_size = src.stat().st_size
    copied_path = None
    if file_size > MAX_FILE_BYTES:
        print(f"  ⚠ File is large ({file_size / 1024 / 1024:.1f} MB > 50 MB limit). "
              f"Storing reference path only (not copying).")
        stored_path = str(src)
        copy_stored = False
    else:
        stored_path = str(src)
        copy_stored = True
        raw_copy_source = stored_path

    meta = generate_metadata()
    data = {
        **meta,
        "type": "file",
        "source": stored_path,
        "content": "",           # text extraction added in Phase 2 classify
        "file_name": src.name,
        "file_extension": src.suffix.lower(),  # edge case E1-18: may be ""
        "file_size_bytes": file_size,
        "file_hash": src_hash,
        "copied_to_raw": copy_stored,
        **({"raw_copy_source": raw_copy_source} if copy_stored else {}),
    }
    path = save_capture(data)
    print(f"  ✓ File captured  →  {path.name}  ({src.name}, {file_size / 1024:.1f} KB)")
    return path


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="capture",
        description="SecondShelf — Capture anything into raw/ with a timestamp + unique ID.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python capture.py note "Just had an idea about RAG pipelines"
  python capture.py url "https://arxiv.org/abs/1706.03762"
  python capture.py file "./notes/meeting-2026-08-01.pdf"
        """,
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # note subcommand
    note_parser = subparsers.add_parser("note", help="Capture a plain-text note")
    note_parser.add_argument("content", help="The note text to capture")
    note_parser.add_argument("--source", default="cli", help="Origin of the note (default: cli)")

    # url subcommand
    url_parser = subparsers.add_parser("url", help="Capture a URL / bookmark")
    url_parser.add_argument("url", help="The URL to capture")

    # file subcommand
    file_parser = subparsers.add_parser("file", help="Capture a file")
    file_parser.add_argument("filepath", help="Path to the file to capture")

    args = parser.parse_args()
    migrate_legacy_json()
    print(f"\n[SecondShelf] Capturing [{args.command}]...")

    if args.command == "note":
        handle_text(args.content, source=args.source)
    elif args.command == "url":
        handle_url(args.url)
    elif args.command == "file":
        handle_file(args.filepath)

    print()


if __name__ == "__main__":
    main()
