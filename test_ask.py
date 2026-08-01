import unittest
import os
import shutil
import tempfile
import json
from pathlib import Path
import frontmatter
import numpy as np

import ask

class MockUtils:
    @staticmethod
    def embed_text(text):
        # Deterministic random vector
        np.random.seed(hash(text) % (2**32))
        return np.random.rand(384).tolist()

class TestAskEngine(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.wiki_dir = Path(self.test_dir) / "wiki"
        self.wiki_dir.mkdir()
        
        ask.WIKI_DIR = self.wiki_dir
        ask.EMBEDDINGS_FILE = Path(self.test_dir) / "embeddings.pkl"
        
        ask.utils = MockUtils()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def create_note(self, uuid, summary, content):
        post = frontmatter.Post(content)
        post.metadata["summary"] = summary
        with open(self.wiki_dir / f"{uuid}.md", "w", encoding="utf-8") as f:
            frontmatter.dump(post, f)

    def test_compute_similarities(self):
        store = {
            "id1": [1, 0, 0],
            "id2": [0.8, 0.2, 0],
            "id3": [0, 1, 0]
        }
        q = [1, 0, 0]
        results = ask.compute_similarities(q, store)
        
        # Sort should put id1 first (sim=1.0), id2 second, id3 last (sim=0)
        self.assertEqual(results[0][0], "id1")
        self.assertAlmostEqual(results[0][1], 1.0)
        self.assertEqual(results[1][0], "id2")
        self.assertEqual(results[2][0], "id3")
        self.assertAlmostEqual(results[2][1], 0.0)

    def test_context_assembly_truncation(self):
        # Test E6-1
        ask.MAX_CONTEXT_CHARS = 100
        
        self.create_note("id1", "Short", "This is fine.")
        self.create_note("id2", "Long", "This content is going to be way too long and will blow past the 100 character limit set for this test.")
        
        top_results = [("id1", 0.9), ("id2", 0.8)]
        
        file_map = {
            "id1": self.wiki_dir / "id1.md",
            "id2": self.wiki_dir / "id2.md"
        }
        
        context_str, sources = ask.assemble_context(top_results, file_map)
        
        # It should include id1, and then truncate id2
        self.assertIn("This is fine", context_str)
        self.assertIn("[TRUNCATED]", context_str)
        self.assertLessEqual(len(context_str), 150) # Approx
        
    def test_empty_wiki_fallback(self):
        # Test E6-3
        result = ask.ask("Hello?")
        self.assertIn("No knowledge base found", result["answer"])

if __name__ == "__main__":
    unittest.main()
