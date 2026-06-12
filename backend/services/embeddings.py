# from sentence_transformers import SentenceTransformer
# from config import Config
from services.model_loader import get_model

# model = SentenceTransformer(Config.EMBEDDING_MODEL)

def create_embeddings(text_chunks):
    model = get_model()
    return model.encode(text_chunks)