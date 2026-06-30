import os

class Config:
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    PINECONE_ENV= os.getenv("PINECONE_ENV")

    UPLOAD_FOLDER = "data/uploads"
    MAX_FILE_SIZE_MB = 10
    PINECONE_INDEX_NAME = "doc-bot-index"
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    DIMENSION = 384
    TOP_K_RESULTS = 5
    # ── Phase 7: Reranker ──
    RETRIEVAL_TOP_K = 20       # How many chunks to fetch before reranking
    RERANKER_MODEL = "BAAI/bge-reranker-base"
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 100

    JWT_SECRET = os.getenv("JWT_SECRET", "doc-bot-secret-key-change-in-production")
    JWT_EXPIRATION_HOURS = 24

    @classmethod
    def validate(cls):
        required = {
            "PINECONE_API_KEY": cls.PINECONE_API_KEY,
            "GROQ_API_KEY": cls.GROQ_API_KEY,
        }

        missing = [
            key
            for key, value in required.items()
            if not value
        ]

        if missing:
            raise ValueError(
                f"Missing environment variables: {', '.join(missing)}"
            )