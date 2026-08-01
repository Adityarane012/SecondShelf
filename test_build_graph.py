import unittest
import os
import shutil
import tempfile
import json
from pathlib import Path
import frontmatter

import build_graph

class TestBuildGraph(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.wiki_dir = Path(self.test_dir) / "wiki"
        self.wiki_dir.mkdir()
        
        build_graph.WIKI_DIR = self.wiki_dir
        build_graph.GRAPH_FILE = Path(self.test_dir) / "graph.json"
        build_graph.EMBEDDINGS_FILE = Path(self.test_dir) / "embeddings.pkl"

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def create_note(self, uuid, category, summary, content, links):
        post = frontmatter.Post(content)
        post.metadata["id"] = uuid
        post.metadata["category"] = category
        post.metadata["summary"] = summary
        post.metadata["links"] = links
        with open(self.wiki_dir / f"{uuid}.md", "w", encoding="utf-8") as f:
            frontmatter.dump(post, f)

    def test_end_to_end_graph(self):
        # Create notes
        self.create_note("id1", "Projects", "Note 1", "Content 1", ["id2", "dangling"])
        self.create_note("id2", "Areas", "Note 2", "Content 2" * 100, ["id1"])
        
        # Test duplicate ID resolution
        self.create_note("id2_dup", "Archives", "Note 2 dup", "Content 2 dup", [])
        # We manually overwrite the internal ID for the dup to test logic
        dup_path = self.wiki_dir / "id2_dup.md"
        post = frontmatter.load(dup_path)
        post.metadata["id"] = "id2"
        with open(dup_path, "w", encoding="utf-8") as f:
            frontmatter.dump(post, f)

        build_graph.build_graph()
        
        self.assertTrue(build_graph.GRAPH_FILE.exists())
        with open(build_graph.GRAPH_FILE, "r", encoding="utf-8") as f:
            graph = json.load(f)
            
        # 1. Duplicate ID ignored, so only 2 nodes total
        self.assertEqual(len(graph["nodes"]), 2)
        
        # 2. Content truncated for node 2
        node2 = next(n for n in graph["nodes"] if n["id"] == "id2")
        self.assertEqual(len(node2["content"]), 303) # 300 + "..."
        
        # 3. Colors mapped correctly
        node1 = next(n for n in graph["nodes"] if n["id"] == "id1")
        self.assertEqual(node1["color"], "#6C63FF")
        self.assertEqual(node2["color"], "#00C9A7")
        
        # 4. Edges deduplicated and dangling ignored
        self.assertEqual(len(graph["edges"]), 1)
        edge = graph["edges"][0]
        self.assertTrue(
            (edge["from"] == "id1" and edge["to"] == "id2") or
            (edge["from"] == "id2" and edge["to"] == "id1")
        )
        self.assertEqual(edge["weight"], 0.65) # fallback weight since no embeddings

if __name__ == "__main__":
    unittest.main()
