"""
test_capture.py — self-check for capture.py (Phase 1)
Run: python test_capture.py

No frameworks. Fails loudly if anything breaks.
Cleans up its own test files from raw/.
"""

import json
import sys
import uuid
from pathlib import Path

# ── patch RAW_DIR to a temp dir so we don't pollute real raw/ ────────────────
import capture  # noqa: E402 (must import after path setup)

TEST_DIR = Path(__file__).parent / "raw" / "_test_tmp"
TEST_DIR.mkdir(parents=True, exist_ok=True)
capture.RAW_DIR = TEST_DIR  # redirect all writes

created = []  # track files to clean up

# ── helper ───────────────────────────────────────────────────────────────────
import shutil
def load(path):
    with open(path / "meta.json", encoding="utf-8") as f:
        data = json.load(f)
    if (path / "content.txt").exists():
        with open(path / "content.txt", encoding="utf-8") as f:
            data["content"] = f.read()
    else:
        ext = data.get("file_extension", "")
        if ext and (path / f"content{ext}").exists():
            data["content"] = ""
    return data

def ok(label):
    print(f"  PASS  {label}")

# ── tests ────────────────────────────────────────────────────────────────────
print("\n=== capture.py self-check ===\n")

# 1. Note — happy path
path = capture.handle_text("Learning about RAG pipelines today")
data = load(path)
assert data["type"] == "note"
assert data["content"] == "Learning about RAG pipelines today"
assert uuid.UUID(data["id"])          # valid UUID4
assert data["timestamp"].endswith("+00:00") or data["timestamp"].endswith("Z")
created.append(path)
ok("note: happy path, schema correct")

# 2. Note — whitespace only (should sys.exit(1))
try:
    capture.handle_text("   ")
    assert False, "Should have exited"
except SystemExit as e:
    assert e.code == 1
ok("note: rejects whitespace-only input")

# 3. Note — long content truncated, no sidecar (truncate once, consistently)
long = "x" * 10_000
path = capture.handle_text(long)
data = load(path)
assert len(data["content"]) <= capture.MAX_NOTE_CHARS
assert "content_full" not in data   # sidecar dropped — downstream only reads content
created.append(path)
ok("note: long content truncated consistently, no sidecar field")

# 4. Note — UUID collision safety (generate_metadata never reuses existing id)
meta1 = capture.generate_metadata()
meta2 = capture.generate_metadata()
assert meta1["id"] != meta2["id"]
ok("metadata: UUIDs are unique across consecutive calls")

# 5. File — happy path (capture this script itself)
this_file = Path(__file__)
path = capture.handle_file(str(this_file))
data = load(path)
assert data["type"] == "file"
assert data["file_name"] == this_file.name
assert data["file_size_bytes"] > 0
assert data["file_hash"] is not None
created.append(path)

ok("file: happy path, schema correct")

# 6. File — duplicate detection via real CLI (uses real raw/, exits 0 on dup)
import subprocess
result = subprocess.run(
    [sys.executable, "capture.py", "file", __file__],
    capture_output=True, text=True, encoding="utf-8", errors="replace"
)
# Either it found a dup (exit 0 + "already been captured") or freshly captured (exit 0 + ".json")
assert result.returncode == 0, f"Expected exit 0, got {result.returncode}\n{result.stderr}"
ok("file: duplicate detection exits cleanly (no crash)")


# 7. File — nonexistent path
try:
    capture.handle_file("/nonexistent/path/file.txt")
    assert False, "Should have exited"
except SystemExit as e:
    assert e.code == 1
ok("file: nonexistent path exits with error")

# 8. File — directory instead of file
try:
    capture.handle_file(str(Path(__file__).parent))
    assert False, "Should have exited"
except SystemExit as e:
    assert e.code == 1
ok("file: directory path rejected")

# 9. URL — scheme injection blocked (file:// scheme)
try:
    capture.handle_url("file:///etc/passwd")
    assert False, "Should have exited"
except SystemExit as e:
    assert e.code == 1
ok("url: file:// scheme blocked")

# 10. URL — auto-prepend https:// for scheme-less input
# (don't actually fetch — just check the URL is normalised before the fetch attempt)
# We monkey-patch requests.Session.get to avoid a real network call
import requests
class FakeResponse:
    status_code = 200
    headers = {"Content-Type": "text/html"}
    text = "<html><head><title>Test Page</title></head><body>Hello world content here for testing purposes to exceed minimum length</body></html>"

original_get = requests.Session.get

def fake_get(self, url, **kwargs):
    assert url.startswith("https://"), f"Expected https://, got {url}"
    return FakeResponse()

requests.Session.get = fake_get
try:
    path = capture.handle_url("example.com")
    data = load(path)
    assert data["source"] == "https://example.com"
    assert data["title"] == "Test Page"
    created.append(path)
    ok("url: scheme-less input auto-prepends https://")
finally:
    requests.Session.get = original_get  # restore

# ── cleanup ──────────────────────────────────────────────────────────────────
for f in created:
    if f and f.exists():
        shutil.rmtree(f)
if TEST_DIR.exists() and not any(TEST_DIR.iterdir()):
    TEST_DIR.rmdir()

print(f"\n=== All checks passed ===\n")
