# SecondShelf — Phase-wise Implementation Plan

> Derived from: `PS.md` (problem statements) + `architecture.md` (system design)
> Build timeline: **4 weeks · 10 phases · 4 milestone badges**

---

## Quick Reference — Phase Map

```
Phase 0  →  Scaffold & Environment Setup          (1 day)
Phase 1  →  Week 1 · Capture Pipeline             (2–3 days)
Phase 2  →  Week 2.1 · Auto-Classify (PARA)       (2 days)
Phase 3  →  Week 2.2 · Auto-Link (Embeddings)     (2 days)
Phase 4  →  Week 3.1 · Graph Data Model           (1 day)
Phase 5  →  Week 3.2 · Interactive Graph UI       (2 days)
Phase 6  →  Week 4.1 · RAG Ask Engine             (2 days)
Phase 7  →  Week 4.2 · Streamlit App Assembly     (2 days)
Phase 8  →  Deploy · Public URL                   (1 day)
Phase 9  →  Polish · README + GitHub              (1 day)
```

---

## Phase 0 — Scaffold & Environment Setup

**Goal**: Get a working, reproducible dev environment before writing a single line of logic.

### Tasks

- [x] Create the repo folder: `SecondShelf/`
- [x] Initialize Git: `git init`
- [x] Create the folder structure:
  ```
  SecondShelf/
  ├── raw/
  ├── wiki/
  ├── static/
  ├── prompts/
  ```
- [x] Create `requirements.txt` with all dependencies:
  ```
  groq
  sentence-transformers
  scikit-learn
  numpy
  python-frontmatter
  python-dotenv
  streamlit
  requests
  beautifulsoup4
  ```
- [x] Create `.env` file (gitignored):
  ```
  GROQ_API_KEY=gsk_...
  SIMILARITY_THRESHOLD=0.65
  TOP_K_RESULTS=5
  ```
- [x] Create `.gitignore` (exclude `.env`, `embeddings.pkl`, `__pycache__/`)
- [x] Run `pip install -r requirements.txt` in a virtual environment
- [ ] Add real GROQ_API_KEY to `.env` and verify Groq API key works with `verify_setup.py`

### Deliverable
> Repo skeleton exists. `pip install` succeeds. Groq API key is validated.

---

## Phase 1 — Week 1 · The Archivist: Capture Pipeline

🏅 **Target Badge**: The Archivist
**Module**: `capture.py`
**Output**: `raw/YYYY-MM-DD_<uuid8>/` (containing `meta.json` and `content.*`)

### Architecture Contract (meta.json)
```json
{
  "id":        "<uuid4>",
  "timestamp": "<ISO-8601>",
  "type":      "note | url | file",
  "source":    "<original input>"
}
```
*Note*: The actual content is stored in a sibling file named `content.txt` (or `content.<ext>`).

### Tasks

#### 1.1 — Core Capture Script
- [x] Import: `uuid`, `datetime`, `json`, `pathlib`, `argparse`
- [x] Implement `generate_metadata()` → returns `{id, timestamp}`
- [x] Implement `save_capture(data: dict)` → writes to `raw/<uuid>.json`

#### 1.2 — Input Handlers
- [x] `handle_text(content: str)` → saves plain text note
- [x] `handle_url(url: str)` → fetches `<title>` + saves URL + extracted text via `requests` + `BeautifulSoup`
- [x] `handle_file(filepath: str)` → copies file to `raw/`, stores path reference

#### 1.3 — CLI Interface
- [x] `argparse` subcommands: `note`, `url`, `file`
  ```bash
  python capture.py note "Idea I had about..."
  python capture.py url "https://example.com"
  python capture.py file "/path/to/doc.pdf"
  ```

#### 1.4 — Real Data Test
- [ ] Run on **10+ real personal items** (not dummy data):
  - At least 3 plain-text notes
  - At least 3 URLs/bookmarks
  - At least 1 file

### Acceptance Criteria
- [x] `raw/` and `wiki/` folder structure exists
- [x] One command captures a note, a link, AND a file
- [x] Every capture has a timestamp + unique ID
- [ ] 10+ real items captured and present in `raw/` ← **Capture your real notes now!**

---

## Phase 2 — Week 2.1 · The Librarian: Auto-Classify

**Module**: `classify.py`
**Input**: `raw/YYYY-MM-DD_<uuid8>/`
**Output**: `wiki/<UUID>.md` (with YAML frontmatter)

### Architecture Contract (wiki note schema)
```yaml
---
id: <uuid>
timestamp: <ISO>
type: note | url | file
category: Projects | Areas | Resources | Archives
tags: [tag1, tag2]
summary: "One-line description"
links: []
---
<original content body>
```

### Tasks

#### 2.1 — Groq API Integration
- [x] Install and configure `groq` client with `GROQ_API_KEY` from `.env`
- [x] Set model: `llama-3.1-8b-instant` (updated from decommissioned llama3-8b-8192)
- [x] Create `prompts/classify_prompt.txt`:
  ```
  Classify the following note using the PARA framework.
  PARA categories: Projects (has deadline/goal), Areas (ongoing responsibility),
  Resources (reference material), Archives (completed/inactive).

  Return ONLY valid JSON in this exact format:
  {"category": "...", "tags": ["...", "..."], "summary": "one line"}

  Note content:
  {content}
  ```

#### 2.2 — Classification Function
- [x] `classify_note(content: str, client, prompt_template) → dict` — calls Groq, parses JSON response
- [x] Add retry logic (max 3 attempts) for API failures
- [x] Add fallback: if JSON parse fails, default to `category: "Resources"`

#### 2.3 — Wiki Writer
- [x] `write_wiki_note(raw_json, classification) → Path` — writes `.md` to `wiki/`
- [x] Use `python-frontmatter` to construct YAML frontmatter
- [x] Initialize `links: []` (to be populated by Phase 3)

#### 2.4 — Batch Processing
- [x] `classify_all()` — iterate all `raw/*/meta.json`, skip already-processed UUIDs
- [x] Print summary: `✓ classified N notes → Projects: X, Areas: Y, Resources: Z, Archives: W`

#### 2.5 — Real Data Test
- [x] Run on all 10+ real captures from Phase 1
- [x] Manually verify PARA categories make sense

### Acceptance Criteria
- [x] Any raw capture → category + tags + summary automatically
- [x] PARA categorization working on real items
- [x] `wiki/` folder contains `.md` files with correct frontmatter

---

## Phase 3 — Week 2.2 · The Librarian: Auto-Link

**Module**: `link.py`
**Input**: `wiki/*.md`
**Output**: Updated `wiki/*.md` (links injected) + `embeddings.pkl`

### Architecture Contract
```
embeddings.pkl  →  dict { "<uuid>": np.array([...]) }
frontmatter links field  →  list of related UUIDs above threshold 0.65
```

### Tasks

#### 3.1 — Embedding Engine
- [x] Load model: `sentence-transformers` → `all-MiniLM-L6-v2` (downloads once, ~80MB)
- [x] `embed_text(text: str) → np.array` — embed a single note's content + summary

#### 3.2 — Persistence Layer
- [x] `load_embeddings() → dict` — load `embeddings.pkl` if exists, else return `{}`
- [x] `save_embeddings(store: dict)` — pickle to `embeddings.pkl`

#### 3.3 — Similarity & Linking
- [x] `find_related(uuid, store, threshold=0.65) → list[str]` — cosine similarity against all stored vectors, return UUIDs above threshold (excluding self)
- [x] `inject_links(uuid, related_uuids)` — read `.md`, update `links:` list in frontmatter, write back
- [x] Make links **bidirectional**: if A links to B, also add A to B's links

#### 3.4 — Incremental Update Pipeline
- [x] `link_all()` — for each note in `wiki/`:
  1. Embed if not already in store
  2. Find related notes
  3. Inject links into frontmatter
  4. Save updated `embeddings.pkl`
- [x] Skip notes where links are already populated (unless `--force` flag)

#### 3.5 — Real Data Test
- [x] Run on 15+ real items
- [x] Print link report: `note X linked to [Y, Z] (similarity: 0.78, 0.71)`

### Acceptance Criteria
- [x] Embeddings computed per note
- [x] Related notes auto-linked (no manual tagging)
- [x] Bidirectional links exist in frontmatter
- [x] Runs on 15+ real items → organized `wiki/`

---

## Phase 4 — Week 3.1 · The Cartographer: Graph Data Model

**Module**: `build_graph.py`
**Input**: `wiki/*.md`
**Output**: `graph.json`

### Architecture Contract
```json
{
  "nodes": [
    {
      "id": "<uuid>",
      "label": "<summary>",
      "category": "Projects | Areas | Resources | Archives",
      "tags": ["tag1"],
      "content": "<full note body>",
      "color": "#6C63FF"
    }
  ],
  "edges": [
    { "from": "<uuid-a>", "to": "<uuid-b>", "weight": 0.73 }
  ]
}
```

### PARA Color Map
```python
COLORS = {
    "Projects":  "#6C63FF",  # purple
    "Areas":     "#00C9A7",  # teal
    "Resources": "#F7B731",  # amber
    "Archives":  "#747D8C",  # grey
}
```

### Tasks

#### 4.1 — Node Builder
- [x] `build_nodes() → list[dict]` — parse each `wiki/*.md` via `python-frontmatter`
- [x] Map `category` → `color` using `COLORS` dict
- [x] Include `content` field (note body, truncated to 500 chars for hover)

#### 4.2 — Edge Builder
- [x] `build_edges(nodes) → list[dict]` — for each node, iterate `links` in frontmatter
- [x] Deduplicate edges (A→B and B→A should be one edge)
- [x] Add `weight` field from cosine similarity (read from embeddings store)

#### 4.3 — Export
- [x] `export_graph(nodes, edges)` → write to `graph.json` (pretty-printed)
- [x] Print stats: `Graph: N nodes, E edges`

### Acceptance Criteria
- [x] Script builds nodes + edges from all notes in `wiki/`
- [x] Exports clean `graph.json`
- [x] Built from real notes, not dummy data

---

## Phase 5 — Week 3.2 · The Cartographer: Interactive Graph UI

**Module**: `static/graph.html`
**Input**: `graph.json`
**Output**: Interactive browser-based force-directed graph

### Tasks

#### 5.1 — vis-network Setup
- [ ] Create `static/graph.html` using vis-network CDN
- [ ] Load `graph.json` via `fetch()` (or embed inline for Streamlit iframe)
- [ ] Configure `vis.Network` with nodes and edges

#### 5.2 — Visual Configuration
- [ ] Force-directed physics: `forceAtlas2Based` or `barnesHut`
- [ ] Node styling:
  - Size proportional to number of links (more connected = bigger)
  - Color from PARA category map
  - Pulsing animation via CSS keyframes on selected nodes
- [ ] Edge styling: width proportional to `weight`, semi-transparent

#### 5.3 — Interactivity
- [ ] **Hover tooltip**: show `summary`, `tags`, `category` on mouse-over
- [ ] **Click**: expand panel showing full note content
- [ ] **Drag**: nodes are draggable
- [ ] **Zoom**: scroll to zoom in/out
- [ ] **Filter buttons**: show/hide by PARA category

#### 5.4 — Streamlit Integration
- [ ] Embed `graph.html` in Streamlit via `st.components.v1.html(html_content, height=600)`
- [ ] Pass `graph.json` content into the HTML as an inline JS variable

### Acceptance Criteria
- [ ] Interactive force-directed graph renders in browser
- [ ] Hover reveals note content
- [ ] Drag + zoom work
- [ ] Color-coded by PARA category

---

## Phase 6 — Week 4.1 · The Oracle: RAG Ask Engine

**Module**: `ask.py`
**Input**: question string + `embeddings.pkl` + `wiki/*.md`
**Output**: answer string with source citations

### Architecture Contract
```python
def ask(question: str) -> dict:
    return {
        "answer": "...",
        "sources": [
            {"id": "<uuid>", "summary": "...", "similarity": 0.81}
        ]
    }
```

### Tasks

#### 6.1 — Query Embedding
- [ ] Reuse `embed_text()` from `link.py` (extract to shared `utils.py`)
- [ ] Embed the incoming question

#### 6.2 — Top-K Retrieval
- [ ] Load `embeddings.pkl`
- [ ] Cosine similarity: question vector vs. all note vectors
- [ ] Return top-`TOP_K_RESULTS` (default 5) note UUIDs, sorted by score

#### 6.3 — Context Assembly
- [ ] Read full content of top-K notes from `wiki/`
- [ ] Build context string (trim to ~3000 tokens to respect LLM context window)
- [ ] Format: `[Note 1 - <summary>]: <content>\n[Note 2 - ...]`

#### 6.4 — LLM Synthesis
- [ ] Create `prompts/ask_prompt.txt`:
  ```
  You are a personal knowledge assistant. Answer the user's question using
  ONLY the notes provided below. Do not use outside knowledge.
  For each fact, cite which note it came from (e.g. "Note 1").
  If the notes don't contain the answer, say so clearly.

  Question: {question}

  Notes:
  {context}
  ```
- [ ] Call Groq (`llama3-8b-8192`) with assembled prompt
- [ ] Return answer + structured source list

#### 6.5 — Testing
- [ ] Test against 5+ real questions about your captured notes
- [ ] Verify citations are accurate
- [ ] Tune `TOP_K_RESULTS` and context truncation

### Acceptance Criteria
- [ ] `ask()` returns synthesized answer from real notes
- [ ] Source citations reference actual note UUIDs/summaries
- [ ] Works on retrieval + LLM in sequence

---

## Phase 7 — Week 4.2 · The Oracle: Streamlit App Assembly

**Module**: `app.py`
**Input**: `graph.json`, `ask.py`, `wiki/*.md`
**Output**: Single Streamlit app with both graph + Q&A

### Tasks

#### 7.1 — App Layout
- [ ] Two-tab layout:
  - Tab 1: `🧠 Brain Graph`
  - Tab 2: `💬 Ask Your Brain`
- [ ] Sidebar with:
  - Quick capture input (text note)
  - PARA filter checkboxes for graph
  - Stats panel: `N notes · E links · PARA breakdown`

#### 7.2 — Brain Graph Tab
- [ ] Load `graph.json`
- [ ] Apply PARA category filter from sidebar
- [ ] Render `static/graph.html` via `st.components.v1.html()`
- [ ] "Refresh Graph" button that re-runs `build_graph.py`

#### 7.3 — Ask Your Brain Tab
- [ ] `st.text_input("Ask anything about your notes...")` with submit button
- [ ] On submit: call `ask(question)`, display answer in styled card
- [ ] Show source notes as `st.expander()` blocks below answer
- [ ] Show "No answer found" gracefully if retrieval fails

#### 7.4 — Quick Capture (Sidebar)
- [ ] Text area + "Capture" button
- [ ] On submit: call `capture.py` logic inline → triggers `classify.py` → `link.py` → `build_graph.py`
- [ ] Show success toast: `✓ Note captured and filed under Resources`

#### 7.5 — Styling
- [ ] Custom CSS via `st.markdown("<style>...</style>", unsafe_allow_html=True)`
- [ ] Dark theme, PARA color accents
- [ ] Smooth loading spinners with `st.spinner()`

### Acceptance Criteria
- [ ] One Streamlit app contains both graph and search bar
- [ ] Full pipeline reachable from the UI
- [ ] Sidebar stats and filters work

---

## Phase 8 — Deploy · Public URL

**Target**: Streamlit Cloud (primary) or HuggingFace Spaces (fallback)

### Tasks

#### 8.1 — Pre-deploy Checklist
- [ ] `requirements.txt` is complete and pinned
- [ ] `.env` is in `.gitignore`
- [ ] `wiki/` and `raw/` contain real data (commit them)
- [ ] `graph.json` and `embeddings.pkl` are committed
- [ ] App runs cleanly with `streamlit run app.py` locally

#### 8.2 — Streamlit Cloud Deploy
- [ ] Push repo to GitHub (public or private)
- [ ] Go to share.streamlit.io → New app → select repo
- [ ] Add secrets in Streamlit Cloud dashboard:
  ```
  GROQ_API_KEY = "gsk_..."
  SIMILARITY_THRESHOLD = "0.65"
  TOP_K_RESULTS = "5"
  ```
- [ ] Click Deploy → wait for build

#### 8.3 — Verify Live App
- [ ] Graph loads and is interactive
- [ ] `ask()` returns answers (not API key errors)
- [ ] Share public URL

### Acceptance Criteria
- [ ] Deployed live with a public URL
- [ ] Interactive graph + ask-anything both functional at the URL
- [ ] Full pipeline works end-to-end in the deployed app

---

## Phase 9 — Polish · README + GitHub

### Tasks

#### 9.1 — README.md
- [ ] Project description + screenshot/GIF of graph
- [ ] Architecture overview (link to `architecture.md`)
- [ ] Setup instructions:
  ```bash
  git clone <repo>
  cd SecondShelf
  pip install -r requirements.txt
  cp .env.example .env   # add GROQ_API_KEY
  python capture.py note "my first note"
  python classify.py
  python link.py
  python build_graph.py
  streamlit run app.py
  ```
- [ ] Live demo link (Streamlit Cloud URL)
- [ ] Badge section: 🏅 Archivist · 🏅 Librarian · 🏅 Cartographer · 🏅 Oracle

#### 9.2 — Final GitHub Push
- [ ] Clean commit history (squash WIP commits)
- [ ] Tag release: `v1.0.0`
- [ ] Verify README renders correctly on GitHub

### Acceptance Criteria
- [ ] Public GitHub repo with clean README + setup instructions
- [ ] All 4 weekly milestones documented and verifiable

---

## Milestone Checklist — Final Sign-off

| # | Week | Badge | Core Modules | Done? |
|---|------|-------|--------------|-------|
| 1 | Week 1 | 🏅 Archivist | `capture.py` | `[ ]` |
| 2 | Week 2 | 🏅 Librarian | `classify.py` + `link.py` | `[ ]` |
| 3 | Week 3 | 🏅 Cartographer | `build_graph.py` + `graph.html` | `[ ]` |
| 4 | Week 4 | 🏅 Oracle | `ask.py` + `app.py` + deploy | `[ ]` |

---

## Shared Utilities — `utils.py` (refactor target)

> Extract these reusable functions once Phase 3 is complete to avoid duplication:

```python
# utils.py
load_wiki_note(uuid)             # parse wiki/<uuid>.md → frontmatter + body
save_wiki_note(uuid, fm, body)   # write back with updated frontmatter
embed_text(text)                 # sentence-transformer embedding
load_embeddings()                # load embeddings.pkl
save_embeddings(store)           # save embeddings.pkl
groq_call(prompt)                # single Groq API wrapper with retry
```

---

## Risk & Mitigation

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Groq rate limit on batch classify | Medium | Add 1s sleep between API calls |
| Embedding model download fails | Low | Cache model locally; use offline flag |
| `graph.json` too large for Streamlit | Low | Truncate `content` field to 300 chars in nodes |
| Cosine similarity too noisy | Medium | Raise threshold to 0.70–0.75 if too many spurious links |
| Streamlit Cloud free tier timeout | Low | Keep `embeddings.pkl` small; lazy-load if needed |
