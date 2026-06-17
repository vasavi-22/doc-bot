from services.vector_store import query_vectors
from services.sparse_retriever import sparse_search
from services.model_loader import get_model

DENSE_WEIGHT = 0.7
SPARSE_WEIGHT = 0.3


def normalize_scores(results):

    if not results:
        return results

    max_score = max(
        r["score"]
        for r in results
    )

    if max_score == 0:
        return results

    for result in results:
        result["score"] /= max_score

    return results


def hybrid_search(
    question,
    top_k=10,
    document_id=None,
    category=None,
    owner=None
):

    # Dense Search
    query_embedding = (
        get_model()
        .encode(question)
        .tolist()
    )

    pinecone_filter = {}

    if document_id:
        pinecone_filter["document_id"] = document_id

    if category:
        pinecone_filter["category"] = category

    if owner:
        pinecone_filter["owner"] = owner

    dense_results = query_vectors(
        query_embedding,
        top_k=top_k,
        filter=pinecone_filter
        if pinecone_filter
        else None
    )

    dense_matches = dense_results.get(
        "matches",
        []
    )

    dense_list = []

    for match in dense_matches:

        dense_list.append({
            "id": match["id"],
            "score": match["score"],
            "metadata": match["metadata"]
        })

    # Sparse Search
    sparse_results = sparse_search(
        query=question,
        top_k=top_k,
        document_id=document_id,
        category=category,
        owner=owner
    )

    # Normalize
    dense_list = normalize_scores(
        dense_list
    )

    sparse_results = normalize_scores(
        sparse_results
    )

    # Merge Scores
    combined = {}

    for item in dense_list:

        combined[item["id"]] = {
            "metadata": item["metadata"],
            "score":
                DENSE_WEIGHT *
                item["score"]
        }

    for item in sparse_results:

        if item["id"] in combined:

            combined[item["id"]]["score"] += (
                SPARSE_WEIGHT *
                item["score"]
            )

        else:

            combined[item["id"]] = {
                "metadata": item["metadata"],
                "score":
                    SPARSE_WEIGHT *
                    item["score"]
            }

    final_results = []

    for chunk_id, value in combined.items():

        final_results.append({
            "id": chunk_id,
            "score": value["score"],
            "metadata": value["metadata"]
        })

    final_results.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return final_results[:top_k]