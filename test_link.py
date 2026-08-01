import unittest
import os
import shutil
import tempfile
from pathlib import Path
import frontmatter
import pickle

import link

class MockSentenceTransformer:
    def __init__(self, model_name):
        self.model_name = model_name
        
    def encode(self, text):
        import numpy as np
        # Return a deterministic random vector based on hash of text
        np.random.seed(hash(text) % (2**32))
        return np.random.rand(384) # Standard dim for minilm

class TestLinkEngine(unittest.TestCase):
    def setUp(self):
        # Create a temp dir for our wiki
        self.test_dir = tempfile.mkdtemp()
        self.wiki_dir = Path(self.test_dir) / "wiki"
        self.wiki_dir.mkdir()
        
        # Override paths in the link module
        link.WIKI_DIR = self.wiki_dir
        link.EMBEDDINGS_FILE = Path(self.test_dir) / "embeddings.pkl"
        
        # Mock the model
        link._model_instance = MockSentenceTransformer("mock-model")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def create_note(self, uuid, summary, content):
        post = frontmatter.Post(content)
        post.metadata["id"] = uuid
        post.metadata["summary"] = summary
        post.metadata["links"] = []
        with open(self.wiki_dir / f"{uuid}.md", "w", encoding="utf-8") as f:
            frontmatter.dump(post, f)

    def test_end_to_end_linking(self):
        # 1. Create a few notes
        self.create_note("id1", "Apple pie recipe", "Apples, sugar, crust.")
        self.create_note("id2", "Cherry pie recipe", "Cherries, sugar, crust.")
        self.create_note("id3", "Car maintenance", "Oil change, tires, brakes.")
        
        # We need to manually set embeddings for id1 and id2 to be very similar 
        # because the mock model just returns random vectors which might not cross threshold
        import numpy as np
        vec_pie = np.ones(384)
        vec_car = np.zeros(384)
        vec_car[0] = 1.0 # avoid div by zero
        
        # Mock embed_note to return these specific vectors
        def mock_embed(uuid, fm_post):
            if uuid in ("id1", "id2"): return vec_pie
            return vec_car
            
        original_embed = link.embed_note
        link.embed_note = mock_embed
        
        try:
            link.link_all()
        finally:
            link.embed_note = original_embed
            
        # 2. Assert embeddings were saved
        self.assertTrue(link.EMBEDDINGS_FILE.exists())
        with open(link.EMBEDDINGS_FILE, "rb") as f:
            store = pickle.load(f)
            self.assertEqual(len(store), 3)
            
        # 3. Assert id1 and id2 linked to each other
        post1 = frontmatter.load(self.wiki_dir / "id1.md")
        post2 = frontmatter.load(self.wiki_dir / "id2.md")
        post3 = frontmatter.load(self.wiki_dir / "id3.md")
        
        self.assertIn("id2", post1.metadata["links"])
        self.assertIn("id1", post2.metadata["links"])
        self.assertEqual(post3.metadata["links"], [])

    def test_prune_embeddings(self):
        store = {"stale_1": [1,2,3], "active_1": [4,5,6]}
        active = {"active_1"}
        pruned = link.prune_embeddings(store, active)
        
        self.assertEqual(pruned, 1)
        self.assertIn("active_1", store)
        self.assertNotIn("stale_1", store)

if __name__ == "__main__":
    unittest.main()
