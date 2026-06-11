from sentence_transformers import SentenceTransformer
from config import Config
from services.model_loader import get_model

# model = SentenceTransformer(Config.EMBEDDING_MODEL)
model = get_model()

def create_embeddings(text_chunks):
    return model.encode(text_chunks)