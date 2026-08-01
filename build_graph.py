"""
build_graph.py — SecondShelf Phase 4: The Cartographer (Graph Data Model)
=================================================
Parses all wiki notes and their semantic links to output a `graph.json`
file containing nodes and edges, ready for visualization.

Usage:
    python build_graph.py
"""

import json
import pickle
import sys
from pathlib import Path
import frontmatter

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent
WIKI_DIR = BASE_DIR / "wiki"
EMBEDDINGS_FILE = BASE_DIR / "embeddings.pkl"
GRAPH_FILE = BASE_DIR / "graph.json"

COLORS = {
    "Projects":  "#6C63FF",  # purple
    "Areas":     "#00C9A7",  # teal
    "Resources": "#F7B731",  # amber
    "Archives":  "#747D8C",  # grey
}
DEFAULT_COLOR = "#F7B731"
MAX_CONTENT_CHARS = 300

def load_embeddings() -> dict:
    if not EMBEDDINGS_FILE.exists():
        return {}
    try:
        with open(EMBEDDINGS_FILE, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        print(f"⚠ Warning: Could not load {EMBEDDINGS_FILE.name}: {e}")
        return {}

def compute_weight(u1: str, u2: str, store: dict) -> float:
    # If embeddings exist, recalculate or look up. 
    # Actually, we can just compute cosine similarity on the fly for the edge weight.
    if u1 in store and u2 in store:
        import numpy as np
        vec1 = np.array(store[u1])
        vec2 = np.array(store[u2])
        # Add small epsilon to avoid div by zero if perfectly 0
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 > 0 and norm2 > 0:
            return float(np.dot(vec1, vec2) / (norm1 * norm2))
    return 0.65  # Default weight if missing

def build_graph():
    if not WIKI_DIR.exists():
        print("Directory wiki/ does not exist. Writing empty graph.")
        write_graph([], [])
        return
        
    store = load_embeddings()
    wiki_files = list(WIKI_DIR.glob("*.md"))
    
    nodes = []
    edges = []
    
    seen_ids = set()
    node_data_map = {}
    
    # E4-1: If no notes, empty graph
    if not wiki_files:
        write_graph([], [])
        print("Graph: 0 nodes, 0 edges")
        return
        
    # Phase 1: Build Nodes
    for fpath in wiki_files:
        try:
            post = frontmatter.load(fpath)
            
            # E4-2: Defaults
            uid = post.metadata.get("id")
            if not uid:
                continue
                
            # E4-3: Deduplicate nodes
            if uid in seen_ids:
                print(f"⚠ Warning: Duplicate ID found for {uid} in {fpath.name}. Skipping.")
                continue
            seen_ids.add(uid)
            
            category = post.metadata.get("category", "Resources")
            label = post.metadata.get("summary", "Untitled Note")
            tags = post.metadata.get("tags", [])
            content = post.content or ""
            
            # E4-6: Truncate content
            if len(content) > MAX_CONTENT_CHARS:
                content = content[:MAX_CONTENT_CHARS] + "..."
                
            node = {
                "id": uid,
                "label": label,
                "category": category,
                "tags": tags,
                "content": content,
                "color": COLORS.get(category, DEFAULT_COLOR),
                "links": post.metadata.get("links", []) # Store temporarily for edge building
            }
            nodes.append(node)
            node_data_map[uid] = node
            
        except Exception as e:
            print(f"⚠ Warning: Could not parse {fpath.name}: {e}")
            
    # Phase 2: Build Edges
    seen_edges = set()
    
    for node in nodes:
        uid = node["id"]
        links = node.pop("links", []) # Remove from final node dict
        
        for target_id in links:
            # E4-4: Dangling links
            if target_id not in seen_ids:
                # Target doesn't exist in wiki, skip
                continue
                
            # E4-7 / Deduplication: ensure A->B and B->A only emit one edge
            # Normalize edge tuple so order doesn't matter
            edge_tuple = tuple(sorted([uid, target_id]))
            
            if edge_tuple not in seen_edges:
                seen_edges.add(edge_tuple)
                weight = compute_weight(edge_tuple[0], edge_tuple[1], store)
                edges.append({
                    "from": edge_tuple[0],
                    "to": edge_tuple[1],
                    "weight": round(weight, 3)
                })
                
    write_graph(nodes, edges)
    print(f"\n🗺️ SecondShelf — The Cartographer")
    print(f"Graph successfully compiled: {len(nodes)} nodes, {len(edges)} edges")

def write_graph(nodes, edges):
    # E4-5: ensure_ascii=False
    data = {"nodes": nodes, "edges": edges}
    with open(GRAPH_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    build_graph()
