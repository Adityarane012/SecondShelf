"""
ask.py — SecondShelf Phase 6: The Oracle (RAG Ask Engine)
=========================================================
Retrieval-Augmented Generation (RAG) engine. Takes a user question,
finds the most relevant notes via embeddings, and asks an LLM
to answer the question using only those notes as context.

Usage:
    python ask.py "What do I know about transformers?"
"""

import os
import sys
import json
import pickle
from pathlib import Path
from dotenv import load_dotenv
import frontmatter
import numpy as np

import utils

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent
WIKI_DIR = BASE_DIR / "wiki"
EMBEDDINGS_FILE = BASE_DIR / "embeddings.pkl"
PROMPT_FILE = BASE_DIR / "prompts" / "ask_prompt.txt"

TOP_K_RESULTS = 5
MAX_CONTEXT_CHARS = 15000

load_dotenv(BASE_DIR / ".env")

def load_embeddings() -> dict:
    if not EMBEDDINGS_FILE.exists():
        return {}
    try:
        with open(EMBEDDINGS_FILE, "rb") as f:
            return pickle.load(f)
    except Exception:
        return {}

def compute_similarities(query_vec, store):
    """Compute cosine similarity of query against all stored vectors."""
    results = []
    q = np.array(query_vec)
    norm_q = np.linalg.norm(q)
    if norm_q == 0:
        return results
        
    for uid, vec in store.items():
        v = np.array(vec)
        norm_v = np.linalg.norm(v)
        if norm_v > 0:
            sim = np.dot(q, v) / (norm_q * norm_v)
            results.append((uid, float(sim)))
    
    # Sort descending by similarity
    results.sort(key=lambda x: x[1], reverse=True)
    return results

def get_file_map() -> dict:
    """Scan wiki/ to map UUIDs back to their Path objects."""
    file_map = {}
    if not WIKI_DIR.exists():
        return file_map
    for fpath in WIKI_DIR.glob("*.md"):
        try:
            post = frontmatter.load(fpath)
            uid = post.metadata.get("id")
            if uid:
                file_map[uid] = fpath
        except Exception:
            pass
    return file_map

def assemble_context(top_results, file_map) -> tuple[str, list[dict]]:
    """Build the context string and return the source metadata."""
    context_parts = []
    sources = []
    
    current_chars = 0
    
    for i, (uid, sim) in enumerate(top_results):
        md_file = file_map.get(uid)
        if not md_file or not md_file.exists():
            continue
            
        try:
            post = frontmatter.load(md_file)
            summary = post.metadata.get("summary", "Untitled")
            content = post.content or ""
            
            # Format: [Note X - summary]: content
            note_str = f"[Note {i+1} - {summary}]:\n{content}\n"
            
            # E6-1: Truncation
            if current_chars + len(note_str) > MAX_CONTEXT_CHARS:
                # Truncate this specific note if adding it blows the limit
                allowed = MAX_CONTEXT_CHARS - current_chars
                if allowed > 30:
                    note_str = note_str[:allowed] + "...[TRUNCATED]\n"
                else:
                    break # Stop adding notes if we're basically full
                    
            context_parts.append(note_str)
            current_chars += len(note_str)
            
            sources.append({
                "id": uid,
                "summary": summary,
                "similarity": round(sim, 3)
            })
            
        except Exception:
            continue
            
    return "\n".join(context_parts), sources

def call_llm(question: str, context: str) -> str:
    """Call Groq API (llama3-8b-8192) with assembled prompt."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "Error: GROQ_API_KEY not found in .env"
        
    try:
        from groq import Groq
    except ImportError:
        return "Error: groq library not installed. Run pip install groq"
        
    if not PROMPT_FILE.exists():
        return f"Error: Prompt template missing at {PROMPT_FILE}"
        
    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        prompt_template = f.read()
        
    prompt = prompt_template.replace("{question}", question).replace("{context}", context)
    
    try:
        client = Groq(api_key=api_key)
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": prompt}
            ],
            model="llama-3.1-8b-instant",
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"LLM API Error: {e}"

def ask(question: str) -> dict:
    """Main RAG interface."""
    store = load_embeddings()
    if not store:
        return {
            "answer": "No knowledge base found. Please capture and link some notes first.",
            "sources": []
        }
        
    # 1. Embed query
    try:
        query_vec = utils.embed_text(question)
    except Exception as e:
        return {
            "answer": f"Embedding error: {e}",
            "sources": []
        }
        
    # 2. Retrieve top K
    similarities = compute_similarities(query_vec, store)
    top_results = similarities[:TOP_K_RESULTS]
    
    if not top_results:
        return {
            "answer": "No relevant notes found.",
            "sources": []
        }
        
    # 3. Assemble Context
    file_map = get_file_map()
    context_str, sources = assemble_context(top_results, file_map)
    
    if not context_str.strip():
        return {
            "answer": "Failed to read relevant note contents.",
            "sources": []
        }
        
    # 4. LLM Synthesis
    answer = call_llm(question, context_str)
    
    return {
        "answer": answer,
        "sources": sources
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ask.py \"Your question here\"")
        sys.exit(1)
        
    question = sys.argv[1]
    print(f"🔮 The Oracle is pondering: '{question}'...\n")
    
    result = ask(question)
    
    print("=== Answer ===")
    print(result["answer"])
    print("\n=== Sources ===")
    for i, src in enumerate(result["sources"]):
        print(f"[{i+1}] {src['summary']} (Sim: {src['similarity']})")
