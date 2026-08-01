# Graph Report - Project SecondBrain  (2026-08-01)

## Corpus Check
- 27 files · ~15,791 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 206 nodes · 221 edges · 26 communities (25 shown, 1 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 2 edges (avg confidence: 0.65)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `31945bf4`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- SecondShelf — Edge Cases & Corner Scenarios
- SecondShelf — Phase-wise Implementation Plan
- Tasks
- capture.py
- SecondShelf — Detailed System Architecture
- Tasks
- Tasks
- Cross-Cutting Concerns
- classify.py
- test_classify.py
- Tasks
- Phase 4 — Week 3.1 · The Cartographer: Graph Data Model
- Tasks
- Tasks
- verify_setup.py
- test_capture.py
- Ponytail, lazy senior dev mode

## God Nodes (most connected - your core abstractions)
1. `SecondShelf — Phase-wise Implementation Plan` - 15 edges
2. `SecondShelf — Edge Cases & Corner Scenarios` - 13 edges
3. `SecondShelf — Detailed System Architecture` - 11 edges
4. `handle_file()` - 8 edges
5. `handle_url()` - 7 edges
6. `classify_all()` - 7 edges
7. `2. Layer-by-Layer Architecture` - 7 edges
8. `save_capture()` - 6 edges
9. `handle_text()` - 6 edges
10. `classify_note()` - 6 edges

## Surprising Connections (you probably didn't know these)
- `check_groq_api()` --calls--> `Groq`  [INFERRED]
  verify_setup.py →   _Bridges community 8 → community 17_

## Import Cycles
- None detected.

## Communities (26 total, 1 thin omitted)

### Community 0 - "SecondShelf — Edge Cases & Corner Scenarios"
Cohesion: 0.08
Nodes (25): 1A — Text Note Capture, 1B — URL Capture, 1C — File Capture, 1D — UUID / Metadata, 2A — Groq API, 2B — Wiki Writer, 3A — Embedding Engine, 3B — Similarity & Linking (+17 more)

### Community 1 - "SecondShelf — Phase-wise Implementation Plan"
Cohesion: 0.10
Nodes (19): 8.1 — Pre-deploy Checklist, 8.2 — Streamlit Cloud Deploy, 8.3 — Verify Live App, 9.1 — README.md, 9.2 — Final GitHub Push, Acceptance Criteria, Acceptance Criteria, Deliverable (+11 more)

### Community 2 - "Tasks"
Cohesion: 0.22
Nodes (9): 3.1 — Embedding Engine, 3.2 — Persistence Layer, 3.3 — Similarity & Linking, 3.4 — Incremental Update Pipeline, 3.5 — Real Data Test, Acceptance Criteria, Architecture Contract, Phase 3 — Week 2.2 · The Librarian: Auto-Link (+1 more)

### Community 3 - "capture.py"
Cohesion: 0.18
Nodes (19): existing_hashes(), existing_urls(), file_hash(), generate_metadata(), handle_file(), handle_text(), handle_url(), main() (+11 more)

### Community 4 - "SecondShelf — Detailed System Architecture"
Cohesion: 0.11
Nodes (17): 10. Suggested Build Order (Cursor-Optimized), 1. High-Level System Overview, 2.1 — Capture Layer (Week 1), 2.2 — Classification Layer (Week 2.1), 2.3 — Auto-Link Layer (Week 2.2), 2.4 — Graph Engine (Week 3), 2.5 — Query / RAG Engine (Week 4.1), 2.6 — UI Layer (Week 4.2) (+9 more)

### Community 5 - "Tasks"
Cohesion: 0.22
Nodes (9): 2.1 — Groq API Integration, 2.2 — Classification Function, 2.3 — Wiki Writer, 2.4 — Batch Processing, 2.5 — Real Data Test, Acceptance Criteria, Architecture Contract (wiki note schema), Phase 2 — Week 2.1 · The Librarian: Auto-Classify (+1 more)

### Community 6 - "Tasks"
Cohesion: 0.22
Nodes (9): 6.1 — Query Embedding, 6.2 — Top-K Retrieval, 6.3 — Context Assembly, 6.4 — LLM Synthesis, 6.5 — Testing, Acceptance Criteria, Architecture Contract, Phase 6 — Week 4.1 · The Oracle: RAG Ask Engine (+1 more)

### Community 7 - "Cross-Cutting Concerns"
Cohesion: 0.40
Nodes (5): CC-1 — Concurrency & Re-entrancy, CC-2 — Data Integrity, CC-3 — Security, CC-4 — Performance, Cross-Cutting Concerns

### Community 8 - "classify.py"
Cohesion: 0.17
Nodes (17): Any, classify_all(), classify_note(), clean_json_response(), get_prompt_template(), init_groq(), main(), Path (+9 more)

### Community 9 - "test_classify.py"
Cohesion: 0.19
Nodes (6): MockChat, MockChoice, MockClient, MockCompletions, MockMessage, test_classify.py — self-check for classify.py (Phase 2) Run: python…

### Community 10 - "Tasks"
Cohesion: 0.25
Nodes (8): 1.1 — Core Capture Script, 1.2 — Input Handlers, 1.3 — CLI Interface, 1.4 — Real Data Test, Acceptance Criteria, Architecture Contract (output schema), Phase 1 — Week 1 · The Archivist: Capture Pipeline, Tasks

### Community 11 - "Phase 4 — Week 3.1 · The Cartographer: Graph Data Model"
Cohesion: 0.25
Nodes (8): 4.1 — Node Builder, 4.2 — Edge Builder, 4.3 — Export, Acceptance Criteria, Architecture Contract, PARA Color Map, Phase 4 — Week 3.1 · The Cartographer: Graph Data Model, Tasks

### Community 12 - "Tasks"
Cohesion: 0.25
Nodes (8): 7.1 — App Layout, 7.2 — Brain Graph Tab, 7.3 — Ask Your Brain Tab, 7.4 — Quick Capture (Sidebar), 7.5 — Styling, Acceptance Criteria, Phase 7 — Week 4.2 · The Oracle: Streamlit App Assembly, Tasks

### Community 15 - "Tasks"
Cohesion: 0.29
Nodes (7): 5.1 — vis-network Setup, 5.2 — Visual Configuration, 5.3 — Interactivity, 5.4 — Streamlit Integration, Acceptance Criteria, Phase 5 — Week 3.2 · The Cartographer: Interactive Graph UI, Tasks

### Community 21 - "test_capture.py"
Cohesion: 0.40
Nodes (3): fake_get(), FakeResponse, test_capture.py — self-check for capture.py (Phase 1) Run: python…

### Community 22 - "Ponytail, lazy senior dev mode"
Cohesion: 0.40
Nodes (4): Codebase map, Git Commit Formatter, GitHub Workflow, Ponytail, lazy senior dev mode

## Knowledge Gaps
- **98 isolated node(s):** `Codebase map`, `GitHub Workflow`, `Git Commit Formatter`, `1. High-Level System Overview`, `2.1 — Capture Layer (Week 1)` (+93 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SecondShelf — Phase-wise Implementation Plan` connect `SecondShelf — Phase-wise Implementation Plan` to `Tasks`, `Tasks`, `Tasks`, `Tasks`, `Phase 4 — Week 3.1 · The Cartographer: Graph Data Model`, `Tasks`, `Tasks`?**
  _High betweenness centrality (0.128) - this node is a cross-community bridge._
- **Why does `Phase 2 — Week 2.1 · The Librarian: Auto-Classify` connect `Tasks` to `SecondShelf — Phase-wise Implementation Plan`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Why does `Phase 3 — Week 2.2 · The Librarian: Auto-Link` connect `Tasks` to `SecondShelf — Phase-wise Implementation Plan`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **What connects `Codebase map`, `GitHub Workflow`, `Git Commit Formatter` to the rest of the system?**
  _98 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `SecondShelf — Edge Cases & Corner Scenarios` be split into smaller, more focused modules?**
  _Cohesion score 0.07692307692307693 - nodes in this community are weakly interconnected._
- **Should `SecondShelf — Phase-wise Implementation Plan` be split into smaller, more focused modules?**
  _Cohesion score 0.1 - nodes in this community are weakly interconnected._
- **Should `SecondShelf — Detailed System Architecture` be split into smaller, more focused modules?**
  _Cohesion score 0.1111111111111111 - nodes in this community are weakly interconnected._