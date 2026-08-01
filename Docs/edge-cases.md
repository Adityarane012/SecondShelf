# SecondShelf — Edge Cases & Corner Scenarios

> Covers every module across all 10 phases of the implementation plan.
> Use this as a test checklist and defensive-coding reference during development.

---

## Table of Contents

1. [Phase 0 — Scaffold & Environment](#phase-0--scaffold--environment)
2. [Phase 1 — Capture Pipeline (`capture.py`)](#phase-1--capture-pipeline)
3. [Phase 2 — Auto-Classify (`classify.py`)](#phase-2--auto-classify)
4. [Phase 3 — Auto-Link (`link.py`)](#phase-3--auto-link)
5. [Phase 4 — Graph Data Model (`build_graph.py`)](#phase-4--graph-data-model)
6. [Phase 5 — Interactive Graph UI (`graph.html`)](#phase-5--interactive-graph-ui)
7. [Phase 6 — RAG Ask Engine (`ask.py`)](#phase-6--rag-ask-engine)
8. [Phase 7 — Streamlit App (`app.py`)](#phase-7--streamlit-app)
9. [Phase 8 — Deployment](#phase-8--deployment)
10. [Cross-Cutting Concerns](#cross-cutting-concerns)

---

## Phase 0 — Scaffold & Environment

| # | Edge Case | Risk | Mitigation |
|---|-----------|------|-----------|
| E0-1 | `GROQ_API_KEY` missing or empty in `.env` | All LLM calls fail silently or with cryptic error | Validate key on startup; raise `EnvironmentError` with clear message |
| E0-2 | `.env` file committed to Git accidentally | API key leaked publicly | Add `.env` to `.gitignore` before first commit; provide `.env.example` |
| E0-3 | Python version < 3.10 (f-strings with `match`, walrus ops) | Syntax errors | Pin `python_requires>=3.10` or add version check at startup |
| E0-4 | `pip install` fails on `sentence-transformers` (no Rust/C++ toolchain) | Phase 3+ unusable | Document build dependencies; offer `--only-binary` fallback |
| E0-5 | `raw/` or `wiki/` already exist with stale data from previous runs | Duplicate or conflicting UUIDs | Check for existing files, don't overwrite; log skipped items |

---

## Phase 1 — Capture Pipeline

### 1A — Text Note Capture

| # | Edge Case | Risk | Mitigation |
|---|-----------|------|-----------|
| E1-1 | Empty string passed as note content | Creates useless `raw/<uuid>.json` with no data | Reject and print `Error: note content cannot be empty` |
| E1-2 | Note is extremely long (> 100k chars, e.g. pasted essay) | LLM token limit exceeded in Phase 2 classify | Truncate `content` to 8000 chars in capture; store full text separately as `raw/<uuid>_full.txt` |
| E1-3 | Note contains special characters: `\n`, `\t`, Unicode emoji, RTL text | JSON serialization breaks | Use `json.dumps(ensure_ascii=False)` |
| E1-4 | Note is pure whitespace | Looks like valid content but is empty | Strip and reject if stripped length == 0 |
| E1-5 | Note in a non-English language | LLM may misclassify PARA category | Acceptable; document as known limitation. Consider adding `language` field to frontmatter |

### 1B — URL Capture

| # | Edge Case | Risk | Mitigation |
|---|-----------|------|-----------|
| E1-6 | URL is malformed (no scheme, typo) | `requests.get()` raises `MissingSchema` | Validate with `urllib.parse`; auto-prepend `https://` if missing |
| E1-7 | URL is unreachable / DNS fails | `ConnectionError` crashes capture | Wrap in `try/except`; save URL as-is with `content: ""` and note `fetch_failed: true` |
| E1-8 | URL returns non-200 status (404, 403, 500) | Empty or error HTML stored as content | Check `response.status_code`; log warning; store URL + status code |
| E1-9 | URL requires JavaScript rendering (SPAs like Notion, Twitter) | `requests` fetches empty HTML shell | Store URL only; flag `js_required: true` in JSON; note in README |
| E1-10 | URL behind a login / paywall | Returns login page HTML instead of content | Detect login-page patterns (e.g. `<form id="login">`); store URL only |
| E1-11 | URL redirects infinitely | `requests` hangs | Set `max_redirects=5`, `timeout=10` |
| E1-12 | Duplicate URL captured twice | Two `raw/*.json` files with identical content | Check if URL already exists in `raw/`; prompt user or skip with warning |
| E1-13 | URL returns binary content (PDF, image) | `BeautifulSoup` parses garbage | Check `Content-Type` header; if not `text/html`, save as file type instead |

### 1C — File Capture

| # | Edge Case | Risk | Mitigation |
|---|-----------|------|-----------|
| E1-14 | File path does not exist | `FileNotFoundError` crashes capture | Check `Path(filepath).exists()` before proceeding |
| E1-15 | File is a directory, not a file | Copy semantics break | Check `Path.is_file()`; reject with clear message |
| E1-16 | File has no read permission | `PermissionError` | Wrap in `try/except PermissionError` |
| E1-17 | File is extremely large (> 50 MB) | Copies huge binary into `raw/` | Warn user; store reference path only rather than copying |
| E1-18 | File has no extension | MIME type unknown | Store as-is; mark `type: "file"`, `extension: ""` |
| E1-19 | Two captures of the same file | Duplicate content | Hash file contents (MD5); warn if hash already exists in `raw/` |

### 1D — UUID / Metadata

| # | Edge Case | Risk | Mitigation |
|---|-----------|------|-----------|
| E1-20 | UUID4 collision (astronomically rare but possible) | Overwrites existing capture | Check if `raw/<uuid>.json` or `raw/*_<uuid>` already exists before writing; regenerate UUID if clash |
| E1-21 | System clock is wrong (far-future or past timestamp) | ISO timestamp is misleading | Log warning if timestamp is > 24h from actual time; don't block capture |
| E1-22 | Partial directory write (crash during save) | Orphaned empty dir or missing content | Write to `.tmp_<uuid>` dir first, then rename to final `YYYY-MM-DD_<uuid>` dir |

---

## Phase 2 — Auto-Classify

### 2A — Groq API

| # | Edge Case | Risk | Mitigation |
|---|-----------|------|-----------|
| E2-1 | Groq API is down / unreachable | All classification fails | Retry 3× with exponential backoff (1s, 2s, 4s); then skip and mark `classified: false` |
| E2-2 | Groq rate limit hit during batch classify | HTTP 429 error mid-batch | Detect 429; sleep for `retry-after` header value; resume |
| E2-3 | LLM returns malformed JSON (extra text, markdown fences) | `json.loads()` raises `JSONDecodeError` | Strip markdown fences (` ```json ``` `); use `re.search(r'\{.*\}', response, re.DOTALL)` to extract JSON |
| E2-4 | LLM returns valid JSON but wrong keys (e.g. `"type"` instead of `"category"`) | Silent data corruption | Validate response against expected schema; raise if keys missing |
| E2-5 | LLM returns a PARA category that isn't in the valid set | Downstream graph coloring breaks | Whitelist: `["Projects", "Areas", "Resources", "Archives"]`; default to `"Resources"` if invalid |
| E2-6 | Note content is too long for LLM context window (8192 tokens for 8B) | API error or truncated response | Pre-truncate `content` to 6000 chars before sending to LLM |
| E2-7 | LLM summary is empty string | Node label is blank in graph | Fall back to first 60 chars of `content` as summary |
| E2-8 | LLM returns 0 tags | No tags in frontmatter | Accept empty list; don't error; tags are optional metadata |

### 2B — Wiki Writer

| # | Edge Case | Risk | Mitigation |
|---|-----------|------|-----------|
| E2-9 | `wiki/<uuid>.md` already exists | Repeated classify run overwrites manual edits | Check existence; skip if present (use `--force` flag to override) |
| E2-10 | `wiki/` directory does not exist | `FileNotFoundError` on write | `Path("wiki").mkdir(exist_ok=True)` at start of `classify_all()` |
| E2-11 | UUID collision in wiki | Note replaced silently | Covered by E1-20 (UUID logic) and E2-9 |
| E2-12 | Corrupted raw JSON (`meta.json` invalid) | `json.load()` throws | Wrap `json.load()` in `try/except`; skip file and log error |
| E2-13 | Missing `content.*` in raw directory | Classification fails | Skip directory if no `content.*` file exists alongside `meta.json` |

---

## Phase 3 — Auto-Link

### 3A — Embedding Engine

| # | Edge Case | Risk | Mitigation |
|---|-----------|------|-----------|
| E3-1 | `all-MiniLM-L6-v2` model not downloaded (offline/first run) | `OSError` on model load | Catch and print: `Run with internet connection first to download the model (~80MB)` |
| E3-2 | Note body is empty (URL capture with `fetch_failed: true`) | Zero-vector or near-zero embedding | Embed the `summary` field as fallback; if both empty, skip embedding |
| E3-3 | Only one note exists in `wiki/` | Cosine similarity has nothing to compare against | Skip linking; log `Only 1 note — need 2+ to auto-link` |
| E3-4 | All notes are about completely different topics | All similarities < 0.65 threshold | Expected behavior; no links created; log `0 links created` (not an error) |
| E3-5 | All notes are about the same topic | Every note links to every other | Raise threshold to 0.75; or cap max links per note to 5 |

### 3B — Similarity & Linking

| # | Edge Case | Risk | Mitigation |
|---|-----------|------|-----------|
| E3-6 | Note compared against itself | Similarity = 1.0 always triggers link | Exclude `uuid == candidate_uuid` in similarity loop |
| E3-7 | `embeddings.pkl` is corrupted (partial write, disk full) | `pickle.load()` raises `UnpicklingError` | Wrap load in `try/except`; delete and rebuild from scratch if corrupt |
| E3-8 | `embeddings.pkl` has stale entries for deleted notes | Ghost edges appear in graph | Cross-check store keys against `wiki/` filenames; prune orphaned entries |
| E3-9 | Bidirectional link injection runs twice | Duplicate UUIDs in `links:` list | Deduplicate `links` list after injection: `links = list(set(links))` |
| E3-10 | Frontmatter `links` field is `null` instead of `[]` | `null + [uuid]` → TypeError | Normalize: `links = fm.get("links") or []` before appending |
| E3-11 | Disk full during `embeddings.pkl` write | Corrupted partial file | Write to `embeddings.pkl.tmp` first, then `rename()` atomically |

---

## Phase 4 — Graph Data Model

| # | Edge Case | Risk | Mitigation |
|---|-----------|------|-----------|
| E4-1 | `wiki/` is empty (no notes processed yet) | `graph.json` has empty nodes/edges | Write valid empty graph `{"nodes": [], "edges": []}`; don't crash |
| E4-2 | A note's frontmatter is missing required fields (`id`, `category`) | `KeyError` during node build | Use `.get()` with defaults: `category = fm.get("category", "Resources")` |
| E4-3 | Two notes have the same `id` in frontmatter (manual edit conflict) | Duplicate node IDs corrupt the graph | Deduplicate by `id`; log warning |
| E4-4 | A link in frontmatter references a UUID that doesn't exist in `wiki/` | Dangling edge in `graph.json` | Validate each link UUID before building edge; skip if target missing |
| E4-5 | Note content contains characters that break JSON serialization (`"`, `\`, control chars) | `json.dumps()` fails or produces invalid JSON | Use `json.dumps(ensure_ascii=False)` with standard escaping; always works |
| E4-6 | `graph.json` grows very large (500+ notes) | Browser render lags or crashes | Truncate `content` field to 300 chars per node for hover; full content fetched on click |
| E4-7 | Circular links (A→B, B→C, C→A) | Graph rendering may loop | Not harmful for vis-network; force-directed layout handles cycles correctly |
| E4-8 | Isolated nodes (no links at all) | Nodes float at edge of graph | Expected; style them smaller/lighter in vis-network config |

---

## Phase 5 — Interactive Graph UI

| # | Edge Case | Risk | Mitigation |
|---|-----------|------|-----------|
| E5-1 | `graph.json` not found when page loads | `fetch()` returns 404; JS error | Show placeholder message: `"Graph not generated yet — run build_graph.py"` |
| E5-2 | `graph.json` has 0 nodes | vis-network renders blank canvas | Show empty state UI: `"No notes yet — start capturing!"` |
| E5-3 | Node label is very long (100+ chars) | Label overflows node circle | Truncate label to 40 chars with `...` suffix in vis-network `label` field |
| E5-4 | Graph has hundreds of nodes (≥ 200) | Force-directed physics is very slow | Disable physics after stabilization: `network.setOptions({physics: {enabled: false}})` |
| E5-5 | User hovers a node very quickly across many nodes | Tooltip flickers or stacks | Debounce hover events by 100ms |
| E5-6 | Hover tooltip content contains HTML tags (from web scraping) | XSS or broken tooltip rendering | Strip HTML tags from `content` field before embedding in tooltip |
| E5-7 | Graph viewed on mobile / small screen | vis-network canvas overflows | Set `canvas` width to `100%`; enable `adaptiveTimestep` for performance |
| E5-8 | All nodes have the same category (e.g. all Resources) | All nodes are the same color — no visual distinction | Expected; graph still usable; categories diversify as more notes are added |
| E5-9 | Browser lacks WebGL support | vis-network canvas may not render | vis-network falls back to 2D canvas; no action needed |
| E5-10 | Streamlit iframe height too small | Graph is clipped, unusable | Set `height=700` in `st.components.v1.html()`; allow user to resize |

---

## Phase 6 — RAG Ask Engine

### 6A — Query & Retrieval

| # | Edge Case | Risk | Mitigation |
|---|-----------|------|-----------|
| E6-1 | `embeddings.pkl` is empty or missing | No notes to retrieve from | Return: `"No notes found. Capture and classify some notes first."` |
| E6-2 | User asks an empty question | Empty embedding; LLM receives empty prompt | Validate `question.strip() != ""`; show input error |
| E6-3 | Question is extremely long (> 500 words) | Embedding model may truncate | Sentence-transformers truncate at 256/512 tokens automatically; acceptable |
| E6-4 | `TOP_K_RESULTS` > total number of notes | Retrieval tries to return more than exists | `k = min(TOP_K_RESULTS, len(embeddings_store))` |
| E6-5 | All cosine similarities are very low (< 0.2) | Retrieved notes are irrelevant to question | Still pass top-K to LLM; prompt instructs it to say `"I don't have notes on this"` |
| E6-6 | Retrieved note files have been deleted since embedding | `FileNotFoundError` on wiki read | Skip missing notes; log warning; don't crash |

### 6B — LLM Synthesis

| # | Edge Case | Risk | Mitigation |
|---|-----------|------|-----------|
| E6-7 | Context assembly exceeds token limit | LLM API error or truncated answer | Trim context: prioritize highest-similarity notes first; hard cap at 3000 chars |
| E6-8 | LLM hallucinates information not in notes | User gets incorrect answer | Prompt explicitly says `"Do NOT use outside knowledge"`; add disclaimer in UI |
| E6-9 | LLM answer is empty string | Blank response shown to user | Fall back: `"The model returned an empty answer. Try rephrasing your question."` |
| E6-10 | Groq API fails mid-answer | Partial or no answer shown | Same retry logic as Phase 2; show error message to user |
| E6-11 | User asks a question in a different language than their notes | LLM may struggle to cross-reference | Acceptable limitation; document in README |
| E6-12 | User asks about a topic captured only once | Only 1 source note returned | Works fine; just 1 source citation |

---

## Phase 7 — Streamlit App

### 7A — State & Session

| # | Edge Case | Risk | Mitigation |
|---|-----------|------|-----------|
| E7-1 | User refreshes page mid-ask | `st.session_state` cleared; answer lost | Expected Streamlit behavior; no persistence needed for MVP |
| E7-2 | User submits empty question via search bar | Calls `ask("")`; LLM prompt is malformed | Validate before calling `ask()`; show inline warning |
| E7-3 | Two browser tabs open the same Streamlit app | Both operate independently | Expected Streamlit behavior; each session is isolated |
| E7-4 | Quick-capture via sidebar captures a note but classify/link fail silently | Note in `raw/` but not in `wiki/` or graph | Show explicit per-step progress: `✓ Captured → ✓ Classified → ✓ Linked → ✓ Graph updated` |

### 7B — File Loading

| # | Edge Case | Risk | Mitigation |
|---|-----------|------|-----------|
| E7-5 | `graph.json` not found at app startup | App crashes on `json.load()` | Wrap in `try/except`; show: `"Run build_graph.py to generate the graph first"` |
| E7-6 | `graph.json` is malformed | `json.JSONDecodeError` | Show error card with instructions to re-run `build_graph.py` |
| E7-7 | `wiki/` has 0 `.md` files | `ask()` retrieval returns nothing | Show: `"Your brain is empty — capture some notes first!"` |
| E7-8 | `embeddings.pkl` missing at startup (no `link.py` run yet) | `ask()` fails immediately | Check existence at startup; disable Ask tab with message if missing |

### 7C — Graph Rendering in Streamlit

| # | Edge Case | Risk | Mitigation |
|---|-----------|------|-----------|
| E7-9 | `st.components.v1.html()` sandboxed iframe blocks `fetch()` calls | `graph.json` can't be fetched from iframe | Inline `graph.json` data as a JS variable in the HTML string instead of `fetch()` |
| E7-10 | PARA filter removes all nodes | Empty graph canvas shown | Show message inside canvas: `"No notes match the selected filters"` |

---

## Phase 8 — Deployment

| # | Edge Case | Risk | Mitigation |
|---|-----------|------|-----------|
| E8-1 | `embeddings.pkl` not committed to GitHub | Streamlit Cloud app starts with no embeddings | Commit `embeddings.pkl`; add note to README |
| E8-2 | `graph.json` not committed | Graph tab is blank on deployed app | Commit `graph.json`; add to pre-deploy checklist |
| E8-3 | Streamlit Cloud secrets not set | `GROQ_API_KEY` is `None`; all LLM calls fail | Add startup check: `if not os.getenv("GROQ_API_KEY"): st.error("GROQ_API_KEY not configured")` |
| E8-4 | `requirements.txt` missing a package | Deploy build fails | Test `pip install -r requirements.txt` in a clean venv before pushing |
| E8-5 | Streamlit Cloud free tier 1GB RAM limit exceeded | App is killed by OOM | Lazy-load `sentence-transformers` model only when `ask()` is called; don't load at startup |
| E8-6 | App deployed but `wiki/` notes contain private information | Public URL exposes private data | Reminder in README: review notes before committing/deploying |
| E8-7 | HuggingFace Spaces uses different secret format | `os.getenv()` returns `None` | HF Spaces uses same `os.environ` — no change needed; just set secrets in HF dashboard |
| E8-8 | Streamlit Cloud cold-start takes > 30s | User sees blank screen | Add `st.spinner("Loading your brain...")` on startup |

---

## Cross-Cutting Concerns

### CC-1 — Concurrency & Re-entrancy

| # | Edge Case | Risk | Mitigation |
|---|-----------|------|-----------|
| CC-1-1 | Two classify/link runs happening simultaneously | Race condition writing same `wiki/<uuid>.md` | Use file-level locking (`filelock` library) or run pipelines sequentially |
| CC-1-2 | `build_graph.py` runs while `link.py` is still writing frontmatter | Partial/inconsistent `graph.json` | Run pipeline steps sequentially; don't parallelize in MVP |

### CC-2 — Data Integrity

| # | Edge Case | Risk | Mitigation |
|---|-----------|------|-----------|
| CC-2-1 | Manual edit of a `wiki/*.md` breaks YAML frontmatter | All downstream modules fail on that file | Wrap every frontmatter parse in `try/except`; skip and log broken files |
| CC-2-2 | UUID in frontmatter doesn't match filename | Data inconsistency | Always use filename UUID as the source of truth; overwrite frontmatter `id` if mismatch |
| CC-2-3 | User deletes a note from `wiki/` but `embeddings.pkl` still has it | Stale vector causes phantom retrieval | `link.py` should prune stale UUIDs from store on every run |
| CC-2-4 | Note content changes after embedding (user edits wiki file) | Old embedding doesn't reflect new content | Re-embed if file `mtime > embedding timestamp`; store `embedded_at` in a sidecar or the store |

### CC-3 — Security

| # | Edge Case | Risk | Mitigation |
|---|-----------|------|-----------|
| CC-3-1 | URL capture fetches a URL with malicious redirect to `file://` | Local file exposure | Reject URLs with non-http(s) schemes |
| CC-3-2 | Note content is injected into LLM prompt (prompt injection attack) | LLM is manipulated to ignore instructions | Since this is a personal tool with user's own notes, risk is low; document as known |
| CC-3-3 | `graph.html` renders user content directly | XSS in hover tooltip | Sanitize `content` field: strip all HTML tags before embedding in JS string |
| CC-3-4 | `GROQ_API_KEY` logged to stdout | Key exposed in server logs | Never log `os.getenv("GROQ_API_KEY")`; use `***` placeholder in debug output |

### CC-4 — Performance

| # | Edge Case | Risk | Mitigation |
|---|-----------|------|-----------|
| CC-4-1 | 500+ notes → similarity matrix is O(n²) | `link.py` takes minutes | Acceptable up to ~1000 notes; beyond that, switch to ChromaDB or FAISS ANN |
| CC-4-2 | `sentence-transformers` model loaded on every script call | 3–5s startup penalty each time | Load model once at module level; don't reload inside loops |
| CC-4-3 | `classify_all()` re-classifies already-classified notes | Wastes Groq API quota | Skip `wiki/*.md` that already exist; track with a set of processed UUIDs |
| CC-4-4 | `graph.json` read on every Streamlit rerun | Slow UI for large graphs | Cache with `@st.cache_data`; invalidate when `graph.json` `mtime` changes |

---

## Edge Case Priority Matrix

| Priority | Edge Cases to Fix Before Shipping |
|----------|----------------------------------|
| 🔴 **P0 — Must fix** | E1-1, E1-6, E1-7, E2-1, E2-3, E2-5, E3-6, E4-4, E6-2, E7-5, E8-3, **E1-20** (UUID collision), **E2-12** (corrupted raw JSON) |
| 🟠 **P1 — Fix before deploy** | E1-12, E2-4, E2-9, E3-7, E3-9, E3-10, E5-6, E6-4, E6-7, E7-4, E8-1, E8-2, CC-2-1 |
| 🟡 **P2 — Nice to have** | E1-5, E1-13, E2-8, E3-4, E3-5, E5-4, E5-5, E6-11, E8-5, CC-4-1, CC-4-4 |
| ⚪ **P3 — Document as known limits** | E1-9, E1-10, E5-8, E6-8, E6-11, CC-3-2, **CC-2-4** (`ponytail: mtime-based re-embed not implemented; wiki edits after link_all() go stale. Fix: store embedded_at in embeddings store, re-embed if mtime > embedded_at`) |
