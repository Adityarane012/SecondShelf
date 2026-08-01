"""
test_classify.py — self-check for classify.py (Phase 2)
Run: python test_classify.py

No frameworks. Fails loudly if anything breaks.
"""

import sys
import json
from pathlib import Path
import frontmatter

import classify

def ok(label):
    print(f"  PASS  {label}")

print("\n=== classify.py self-check ===\n")

# 1. Clean JSON response (E2-3)
raw_response = "```json\n{\"category\": \"Projects\", \"tags\": [\"a\"], \"summary\": \"s\"}\n```"
cleaned = classify.clean_json_response(raw_response)
assert "```" not in cleaned
parsed = json.loads(cleaned)
assert parsed["category"] == "Projects"
ok("clean_json_response strips markdown fences")

# 2. Test fallback on bad keys (E2-4, E2-5)
# Mock the Groq client
class MockMessage:
    def __init__(self, content):
        self.content = content
class MockChoice:
    def __init__(self, content):
        self.message = MockMessage(content)
class MockCompletions:
    def __init__(self, response_text):
        self.response_text = response_text
    def create(self, **kwargs):
        return type("MockResponse", (), {"choices": [MockChoice(self.response_text)]})()
class MockChat:
    def __init__(self, response_text):
        self.completions = MockCompletions(response_text)
class MockClient:
    def __init__(self, response_text):
        self.chat = MockChat(response_text)

# E2-4: Wrong keys
client = MockClient('{"wrong_key": "Projects"}')
result = classify.classify_note("test", client, "prompt")
assert result["category"] == "Resources", f"Expected fallback, got {result}"
ok("classify_note falls back to Resources on missing keys")

# E2-5: Invalid Category
client = MockClient('{"category": "Invalid", "tags": [], "summary": "test"}')
result = classify.classify_note("test", client, "prompt")
assert result["category"] == "Resources"
ok("classify_note falls back to Resources on invalid category")

# E2-8: Invalid tags type
client = MockClient('{"category": "Projects", "tags": "not a list", "summary": "test"}')
result = classify.classify_note("test", client, "prompt")
assert result["tags"] == []
ok("classify_note resets tags to empty list if not a list")

# 3. Test Wiki Writer
test_raw = {
    "id": "1234",
    "timestamp": "2026-08-01",
    "type": "note",
    "source": "cli",
    "content": "Test body content"
}
test_classification = {
    "category": "Projects",
    "tags": ["test"],
    "summary": ""  # E2-7: empty summary test
}

test_md = Path("_test_wiki.md")
try:
    classify.write_wiki_note(test_raw, test_classification, test_md)
    post = frontmatter.load(test_md)
    assert post.metadata["id"] == "1234"
    assert post.metadata["category"] == "Projects"
    assert post.metadata["tags"] == ["test"]
    assert post.metadata["summary"] == "Test body content"  # Fallback worked
    assert post.content == "Test body content"
    ok("write_wiki_note generates correct frontmatter and applies summary fallback")
finally:
    if test_md.exists():
        test_md.unlink()

print(f"\n=== All checks passed ===\n")
