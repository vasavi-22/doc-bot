from sentence_transformers import SentenceTransformer
from config import Config

model = SentenceTransformer(Config.EMBEDDING_MODEL)

def create_embeddings(text_chunks):
    return model.encode(text_chunks)