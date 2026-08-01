"""
classify.py — SecondShelf Phase 2: The Librarian
=================================================
Auto-classifies raw JSON captures using Groq (llama3-8b-8192) into the PARA framework.
Writes the classified notes as Markdown files with YAML frontmatter in wiki/.

Usage:
    python classify.py          # Classify all unclassified raw notes
    python classify.py --force  # Re-classify and overwrite existing wiki notes
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv
import frontmatter
from groq import Groq
import groq

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ─── Constants ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
RAW_DIR = BASE_DIR / "raw"
WIKI_DIR = BASE_DIR / "wiki"
PROMPTS_DIR = BASE_DIR / "prompts"
PROMPT_FILE = PROMPTS_DIR / "classify_prompt.txt"

MODEL_NAME = "llama-3.1-8b-instant"
MAX_CONTENT_CHARS = 6000  # Edge case E2-6
VALID_CATEGORIES = {"Projects", "Areas", "Resources", "Archives"}

# Load environment variables
load_dotenv(BASE_DIR / ".env")


def init_groq() -> Groq:
    """Initialize Groq client."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or api_key == "gsk_...":
        print("Error: GROQ_API_KEY is missing or invalid in .env")
        sys.exit(1)
    return Groq(api_key=api_key)


def get_prompt_template() -> str:
    """Load the classification prompt template."""
    if not PROMPT_FILE.exists():
        print(f"Error: Prompt file not found at {PROMPT_FILE}")
        sys.exit(1)
    return PROMPT_FILE.read_text(encoding="utf-8")


def clean_json_response(text: str) -> str:
    """Extract JSON from LLM response (Edge case E2-3)."""
    # Strip markdown fences if present
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    return text


def classify_note(content: str, client: Groq, prompt_template: str) -> Dict[str, Any]:
    """Call Groq API to classify content, handling retries and rate limits."""
    # Edge case E2-6: Truncate before sending to LLM to stay under token limits
    if len(content) > MAX_CONTENT_CHARS:
        content = content[:MAX_CONTENT_CHARS]
        
    prompt = prompt_template.replace("{content}", content)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=MODEL_NAME,
                temperature=0.1,  # Low temperature for consistent JSON output
            )
            raw_result = response.choices[0].message.content
            cleaned = clean_json_response(raw_result)
            
            try:
                parsed = json.loads(cleaned)
            except json.JSONDecodeError:
                # E2-3 fallback
                print("  ⚠ Failed to parse JSON from LLM response. Defaulting to Resources.")
                return {"category": "Resources", "tags": [], "summary": ""}
            
            # E2-4: Validate keys
            if not isinstance(parsed, dict) or "category" not in parsed or "summary" not in parsed or "tags" not in parsed:
                print("  ⚠ Missing required keys in LLM response. Defaulting to Resources.")
                return {"category": "Resources", "tags": [], "summary": ""}
                
            # E2-5: Validate category
            if parsed["category"] not in VALID_CATEGORIES:
                parsed["category"] = "Resources"
                
            # E2-8: Tags must be a list
            if not isinstance(parsed["tags"], list):
                parsed["tags"] = []
                
            return parsed

        except groq.RateLimitError as e:
            # E2-2: Rate limit hit
            retry_after = 5 # default 5s
            # Try to parse retry-after from error message if available, groq exceptions might wrap it
            msg = str(e).lower()
            if "please try again in" in msg:
                try:
                    # simplistic extraction: "Please try again in 3s."
                    s = msg.split("please try again in ")[1]
                    retry_after = float(s.split("s")[0].strip())
                except:
                    pass
            
            if attempt < max_retries - 1:
                print(f"  ⚠ Rate limit hit. Waiting {retry_after}s before retry ({attempt + 1}/{max_retries})...")
                time.sleep(retry_after)
            else:
                print("  ⚠ Rate limit retries exhausted. Skipping.")
                return {"category": "Resources", "tags": [], "summary": ""}
                
        except groq.APIConnectionError as e:
            # E2-1: API down or unreachable
            if attempt < max_retries - 1:
                backoff = 2 ** attempt
                print(f"  ⚠ API Connection Error. Retrying in {backoff}s ({attempt + 1}/{max_retries})...")
                time.sleep(backoff)
            else:
                print(f"  ⚠ API Connection Errors exhausted. Skipping.")
                return {"category": "Resources", "tags": [], "summary": ""}
                
        except Exception as e:
            print(f"  ⚠ Unexpected API error: {e}")
            return {"category": "Resources", "tags": [], "summary": ""}
            
    return {"category": "Resources", "tags": [], "summary": ""}


def write_wiki_note(raw_data: Dict[str, Any], classification: Dict[str, Any], out_path: Path):
    """Write the classified note as a Markdown file with YAML frontmatter."""
    post = frontmatter.Post(raw_data.get("content", ""))
    
    post.metadata["id"] = raw_data["id"]
    post.metadata["timestamp"] = raw_data["timestamp"]
    post.metadata["type"] = raw_data["type"]
    post.metadata["category"] = classification["category"]
    post.metadata["tags"] = classification["tags"]
    
    # E2-7: empty summary fallback
    summary = classification["summary"]
    if not summary or not str(summary).strip():
        content = raw_data.get("content", "")
        summary = content[:60].strip() + "..." if len(content) > 60 else content
    post.metadata["summary"] = summary
    post.metadata["links"] = []  # To be populated by Phase 3
    
    # Keep original source if available
    if "source" in raw_data:
        post.metadata["source"] = raw_data["source"]
        
    with open(out_path, "w", encoding="utf-8") as f:
        frontmatter.dump(post, f)


def classify_all(force: bool = False):
    """Process all JSON files in raw/."""
    # E2-10: Ensure wiki dir exists
    WIKI_DIR.mkdir(exist_ok=True)
    
    if not RAW_DIR.exists():
        print(f"Directory {RAW_DIR} does not exist. Nothing to classify.")
        return
        
    client = init_groq()
    prompt_template = get_prompt_template()
    
    raw_files = list(RAW_DIR.glob("*/meta.json"))
    if not raw_files:
        print("No raw notes found to classify.")
        return
        
    stats = {"Projects": 0, "Areas": 0, "Resources": 0, "Archives": 0, "Skipped": 0, "Errors": 0}
    
    print(f"\n📚 SecondShelf — The Librarian")
    print(f"Found {len(raw_files)} raw files to process.\n")
    
    for meta_file in raw_files:
        folder = meta_file.parent
        out_path = WIKI_DIR / f"{folder.name}.md"
        
        # E2-9: Check existence
        if out_path.exists() and not force:
            stats["Skipped"] += 1
            continue
            
        print(f"Classifying {folder.name}...")
        
        # E2-12: Corrupted raw JSON
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except json.JSONDecodeError:
            print(f"  ✗ Error: File {meta_file.name} is corrupted (invalid JSON). Skipping.")
            stats["Errors"] += 1
            continue
            
        # E2-13: Extract content from sibling files
        content = ""
        content_txt = folder / "content.txt"
        if content_txt.exists():
            with open(content_txt, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        else:
            # Maybe it's a binary file
            ext = raw_data.get("file_extension", "")
            if ext and (folder / f"content{ext}").exists():
                content = "" # Binary file content is skipped for LLM
            else:
                print(f"  ⚠ Missing content file in {folder.name}. Skipping classification.")
                stats["Errors"] += 1
                continue
                
        # Attach content to raw_data so write_wiki_note gets it
        raw_data["content"] = content
        
        # Special case: if content is empty (e.g. failed fetch), we can just mark it Resources
        if not content.strip():
            print("  ℹ Empty content, assigning to Resources.")
            classification = {"category": "Resources", "tags": [], "summary": "Empty capture"}
        else:
            classification = classify_note(content, client, prompt_template)
            
        write_wiki_note(raw_data, classification, out_path)
        stats[classification["category"]] += 1
        print(f"  ✓ {classification['category']} | Tags: {len(classification['tags'])}")
        
        # Tiny sleep to avoid hammering the API if there are many files
        time.sleep(0.5)

    print("\n=== Classification Summary ===")
    print(f"Projects:  {stats['Projects']}")
    print(f"Areas:     {stats['Areas']}")
    print(f"Resources: {stats['Resources']}")
    print(f"Archives:  {stats['Archives']}")
    print(f"Skipped:   {stats['Skipped']}")
    print(f"Errors:    {stats['Errors']}")
    print("==============================\n")


def main():
    parser = argparse.ArgumentParser(description="Auto-classify raw notes into PARA framework.")
    parser.add_argument("--force", action="store_true", help="Re-classify and overwrite existing wiki notes")
    args = parser.parse_args()
    classify_all(force=args.force)


if __name__ == "__main__":
    main()
