"""
app.py — SecondShelf Phase 5 & 7: The Cartographer & The Oracle
=================================================================
Streamlit application to visualize the knowledge graph and (soon) ask questions.

Usage:
    streamlit run app.py
"""

import streamlit as st
import json
from pathlib import Path
import streamlit.components.v1 as components

BASE_DIR = Path(__file__).parent
GRAPH_FILE = BASE_DIR / "graph.json"
STATIC_DIR = BASE_DIR / "static"
GRAPH_HTML_FILE = STATIC_DIR / "graph.html"

st.set_page_config(
    page_title="SecondShelf Brain Graph",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

def load_graph_data():
    """Load graph.json safely (E5-1, E5-2)."""
    if not GRAPH_FILE.exists():
        return None
    try:
        with open(GRAPH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error reading graph data: {e}")
        return None

def main():
    st.title("🧠 SecondShelf Brain Graph")
    
    # In Phase 7 we will add tabs. For now, just render the graph.
    graph_data = load_graph_data()
    
    if not graph_data:
        st.info("Graph not generated yet. Please run `python build_graph.py` first.")
        return
        
    if not graph_data.get("nodes"):
        st.info("No notes found in the graph. Start capturing notes and rebuild the graph!")
        return

    # Load HTML template
    if not GRAPH_HTML_FILE.exists():
        st.error(f"Missing {GRAPH_HTML_FILE.name} template.")
        return
        
    with open(GRAPH_HTML_FILE, "r", encoding="utf-8") as f:
        html_template = f.read()
        
    # Inject JSON payload into HTML
    json_payload = json.dumps(graph_data, ensure_ascii=False)
    # Using replace ensures we don't trip over other brackets
    html_content = html_template.replace("__GRAPH_JSON_PAYLOAD__", json_payload)
    
    st.markdown("Interact with your knowledge graph below. Scroll to zoom, drag to pan.")
    
    # Render with Streamlit Components
    components.html(html_content, height=700)

if __name__ == "__main__":
    main()
