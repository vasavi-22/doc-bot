from sentence_transformers import SentenceTransformer
from config import Config

_model = None

def get_model():
    global _model

    if _model is None:
        _model = SentenceTransformer(Config.EMBEDDING_MODEL)

    return _model