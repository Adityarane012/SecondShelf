"""
link.py — SecondShelf Phase 3: The Cartographer
=================================================
Auto-links wiki notes by computing semantic similarity using sentence-transformers.
Updates wiki/*.md files by injecting a `links` array in the YAML frontmatter.

Usage:
    python link.py          # Process unlinked notes
    python link.py --force  # Re-embed and re-link all notes
"""

import argparse
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

MODEL_NAME = "all-MiniLM-L6-v2"
SIMILARITY_THRESHOLD = 0.65
MAX_LINKS_PER_NOTE = 5

_model_instance = None

def get_model():
    """Lazy load sentence-transformers model (E3-1)."""
    global _model_instance
    if _model_instance is None:
        try:
            # We import here so the CLI boots fast if no embedding is needed
            from sentence_transformers import SentenceTransformer
            import urllib.request
            # Check for internet to warn (E3-1)
            try:
                urllib.request.urlopen("https://huggingface.co", timeout=3)
            except Exception:
                print(f"⚠ Warning: Offline mode. Loading model from cache (if available).")
                print(f"If this crashes, run with an internet connection first to download the model (~80MB).")
                
            _model_instance = SentenceTransformer(MODEL_NAME)
        except OSError as e:
            print(f"Error loading model '{MODEL_NAME}': {e}")
            print("Run with an internet connection first to download the model (~80MB).")
            sys.exit(1)
        except ImportError:
            print("Error: sentence-transformers not installed. Run: pip install sentence-transformers")
            sys.exit(1)
    return _model_instance


def load_embeddings() -> dict:
    """Load embeddings.pkl if exists, else return {}. Handles corruption (E3-7)."""
    if not EMBEDDINGS_FILE.exists():
        return {}
    try:
        with open(EMBEDDINGS_FILE, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        print(f"⚠ Warning: {EMBEDDINGS_FILE.name} corrupted ({e}). Rebuilding from scratch.")
        EMBEDDINGS_FILE.unlink(missing_ok=True)
        return {}


def save_embeddings(store: dict):
    """Save embeddings using atomic write (E3-11)."""
    tmp_file = EMBEDDINGS_FILE.with_suffix(".tmp")
    with open(tmp_file, "wb") as f:
        pickle.dump(store, f)
    tmp_file.replace(EMBEDDINGS_FILE)


def prune_embeddings(store: dict, active_uuids: set) -> int:
    """Remove embeddings for notes that no longer exist (E3-8)."""
    stale = [uid for uid in store if uid not in active_uuids]
    for uid in stale:
        del store[uid]
    return len(stale)


def get_wiki_notes() -> list[Path]:
    if not WIKI_DIR.exists():
        return []
    return list(WIKI_DIR.glob("*.md"))


def embed_note(uuid: str, fm_post: frontmatter.Post) -> object:
    """Compute embedding for a single note (E3-2). Returns numpy array or tensor."""
    # Combine summary and content to maximize context
    summary = fm_post.metadata.get("summary", "")
    content = fm_post.content or ""
    
    # E3-2 fallback
    text = f"{summary}\n{content}".strip()
    if not text:
        return None
        
    model = get_model()
    return model.encode(text)


def link_all(force: bool = False):
    """Main linking pipeline."""
    wiki_files = get_wiki_notes()
    if not wiki_files:
        print("No wiki files found.")
        return

    store = load_embeddings()
    
    # Map UUID -> Path and cleanup store
    active_uuids = set()
    uuid_to_path = {}
    
    for fpath in wiki_files:
        try:
            post = frontmatter.load(fpath)
            uid = post.metadata.get("id")
            if uid:
                active_uuids.add(uid)
                uuid_to_path[uid] = fpath
        except Exception as e:
            print(f"⚠ Warning: Could not parse frontmatter for {fpath.name}: {e}")

    pruned = prune_embeddings(store, active_uuids)
    if pruned:
        print(f"ℹ Pruned {pruned} orphaned embeddings.")

    # 1. Embed missing notes
    embedded_count = 0
    for uid, fpath in uuid_to_path.items():
        if uid not in store or force:
            # ponytail: mtime-based re-embed not implemented, edits after linking go stale unless --force is used.
            post = frontmatter.load(fpath)
            emb = embed_note(uid, post)
            if emb is not None:
                store[uid] = emb
                embedded_count += 1
            else:
                print(f"⚠ Skipped empty note {uid}")

    if embedded_count > 0 or pruned > 0:
        save_embeddings(store)
        print(f"ℹ Generated {embedded_count} new embeddings.")

    # E3-3: Need at least 2 notes to link
    if len(store) < 2:
        print("Only 1 note — need 2+ to auto-link.")
        return

    # 2. Similarity & Linking
    from sentence_transformers import util
    import torch
    import numpy as np
    
    print(f"\n🗺️ SecondShelf — The Cartographer")
    print(f"Computing semantic links across {len(store)} notes...\n")
    
    # Convert store to tensors for fast batch similarity
    uids = list(store.keys())
    embeddings_list = [store[u] for u in uids]
    
    # embeddings_tensor might be a list of numpy arrays, convert to tensor
    if isinstance(embeddings_list[0], np.ndarray):
        embeddings_tensor = torch.tensor(np.array(embeddings_list))
    elif not isinstance(embeddings_list[0], torch.Tensor):
        embeddings_tensor = torch.tensor(embeddings_list)
    else:
        # If it's already tensors, stack them
        embeddings_tensor = torch.stack(embeddings_list)
        
    # cos_sim returns a matrix of similarities [N, N]
    sim_matrix = util.cos_sim(embeddings_tensor, embeddings_tensor)
    
    links_added = 0
    
    # Extract edges
    edges = []
    for i in range(len(uids)):
        for j in range(i + 1, len(uids)):
            score = sim_matrix[i][j].item()
            if score > SIMILARITY_THRESHOLD:
                edges.append((uids[i], uids[j], score))
                
    # Sort edges by score descending
    edges.sort(key=lambda x: x[2], reverse=True)
    
    # Track connections to enforce E3-5 (max links)
    connections = {uid: set() for uid in uids}
    
    for u1, u2, score in edges:
        if len(connections[u1]) < MAX_LINKS_PER_NOTE and len(connections[u2]) < MAX_LINKS_PER_NOTE:
            connections[u1].add(u2)
            connections[u2].add(u1)
            
    # Inject links into files
    for uid, targets in connections.items():
        if not targets:
            continue
            
        fpath = uuid_to_path.get(uid)
        if not fpath: continue
        
        post = frontmatter.load(fpath)
        existing_links = post.metadata.get("links") or [] # E3-10
        
        # Determine if we actually need to write
        new_links = list(set(existing_links + list(targets))) # E3-9
        new_links.sort()
        
        # Only rewrite if there's a diff
        if set(existing_links) != set(new_links):
            post.metadata["links"] = new_links
            with open(fpath, "w", encoding="utf-8") as f:
                frontmatter.dump(post, f)
            links_added += len(set(new_links) - set(existing_links))
            print(f"  ✓ {fpath.name} linked to {len(targets)} notes")
            
    if links_added == 0:
        print("0 new links created.")
    else:
        print(f"\n=== Linking Summary ===")
        print(f"Total new link edges injected: {links_added}")
        print("=======================\n")


def main():
    parser = argparse.ArgumentParser(description="Auto-link wiki notes based on semantic similarity.")
    parser.add_argument("--force", action="store_true", help="Re-embed and re-link all notes")
    args = parser.parse_args()
    link_all(force=args.force)


if __name__ == "__main__":
    main()
