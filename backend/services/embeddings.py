from services.model_loader import get_model

def create_embeddings(text_chunks):
    model = get_model()
    return model.encode(text_chunks)