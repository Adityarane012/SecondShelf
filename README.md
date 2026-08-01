# 🧠 SecondShelf

SecondShelf is an automated, AI-powered "Second Brain" built on top of the PARA framework. It transforms messy, raw notes into a beautifully categorized, semantically linked, and fully queryable knowledge base—entirely automatically.

## 🚀 Features

- **Instant Capture**: Dump raw thoughts, URLs, and files instantly via the CLI without worrying about organization.
- **AI Classification**: Automatically structures and categorizes notes into Projects, Areas, Resources, and Archives using Groq (Llama-3.1).
- **Semantic Auto-Linking**: Runs a local embedding model (`sentence-transformers`) to discover hidden relationships between your notes and weaves them together using bidirectional links.
- **Interactive Graph UI**: A browser-based force-directed knowledge graph to visually explore how your thoughts connect.
- **The Oracle (RAG Engine)**: Ask conversational questions and get answers synthesized directly from your notes, complete with source citations.

## ⚙️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Adityarane012/SecondShelf.git
   cd SecondShelf
   ```

2. **Install dependencies:**
   Ensure you have Python 3.10+ installed, then run:
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Setup:**
   Create a `.env` file in the root directory and add your Groq API key:
   ```env
   GROQ_API_KEY=your_api_key_here
   ```

## 📖 Usage Guide

SecondShelf operates as a pipeline of independent scripts. You capture data, then run the pipeline to organize and link it.

### 1. Capture (`capture.py`)
Quickly dump raw information into the `raw/` directory.
```bash
python capture.py note "I have an idea for a new app"
python capture.py file document.txt
python capture.py url https://example.com
```

### 2. Classify (`classify.py`)
Processes raw data, summarizes it, tags it, categorizes it into PARA, and writes clean Markdown files into the `wiki/` directory.
```bash
python classify.py
```

### 3. Link (`link.py`)
Reads all notes in your `wiki/`, computes their semantic meaning, and injects links between related notes directly into their YAML frontmatter.
```bash
python link.py
```

### 4. Build Graph (`build_graph.py`)
Compiles the notes and semantic links into a lightweight `graph.json` structure for visualization.
```bash
python build_graph.py
```

### 5. View Graph UI (`app.py`)
Launches the interactive knowledge graph in your web browser.
```bash
streamlit run app.py
```

### 6. Ask Questions (`ask.py`)
Use the Retrieval-Augmented Generation (RAG) engine to ask questions and get cited answers from your notes.
```bash
python ask.py "What did I write about machine learning?"
```

## 🏗️ Architecture

- **LLM**: [Groq](https://groq.com/) running `llama-3.1-8b-instant` for blazing fast categorization and Q&A synthesis.
- **Embeddings**: Local `all-MiniLM-L6-v2` via `sentence-transformers` for fast, offline semantic linking.
- **Graph Visualization**: `vis-network` rendered inside a `Streamlit` application.
- **Storage**: Plain-text Markdown files with YAML frontmatter. Future-proof and entirely portable!
