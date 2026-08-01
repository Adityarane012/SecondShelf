"""
utils.py — SecondShelf Shared Utilities
"""

import sys

# Attempt to load sentence-transformers. If missing, fail gracefully.
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

# We use a singleton instance so we don't load the model into memory multiple times
_model_instance = None

def get_model():
    global _model_instance
    if _model_instance is None:
        if SentenceTransformer is None:
            raise ImportError("sentence-transformers is not installed.")
        _model_instance = SentenceTransformer("all-MiniLM-L6-v2")
    return _model_instance

def embed_text(text: str) -> list[float]:
    """
    Takes a string and returns a vector embedding.
    """
    model = get_model()
    # model.encode returns a numpy array, convert to standard python list for json/pickle ease
    vector = model.encode(text)
    return vector.tolist()

