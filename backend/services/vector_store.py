import os
from pinecone import Pinecone, ServerlessSpec
import uuid

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

INDEX_NAME = "doc-bot-index"
DIMENSION = 384


def init_index():
    existing_indexes = [i["name"] for i in pc.list_indexes()]

    if INDEX_NAME not in existing_indexes:
        pc.create_index(
            name=INDEX_NAME,
            dimension=DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )

    return pc.Index(INDEX_NAME)


def store_vectors(chunks, embeddings, metadata_list=None):
    index = init_index()

    vectors = []

    for i, embedding in enumerate(embeddings):
        vectors.append({
            "id": str(uuid.uuid4()),
            "values": embedding,
            "metadata": {
                "text": chunks[i],
                **(metadata_list[i] if metadata_list else {})
            }
        })

    index.upsert(vectors=vectors)

    return {"status": "success", "count": len(vectors)}


# ✅ ADD THIS (important)
def query_vectors(query_embedding, top_k=3):
    index = init_index()

    return index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True
    )