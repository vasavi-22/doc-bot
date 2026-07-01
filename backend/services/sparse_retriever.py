from rank_bm25 import BM25Okapi
from database import get_chunks

def tokenize(text):
    return text.lower().split()


def sparse_search(
    query,
    top_k=10,
    document_id=None,
    category=None,
    owner=None,
    user_id=None,
    filter_document_ids=None,
    filter_categories=None,
    filter_tags=None,
    user_role=None
):

    # ── Phase 8: RBAC – Role-aware chunk fetching ──
    if user_role == "admin":
        # Admin sees everything — no user_id filter needed
        rows = get_chunks(
            document_id=document_id,
            category=category,
            owner=owner,
            user_id=None
        )
    else:
        # Employee sees only their own chunks
        rows = get_chunks(
            document_id=document_id,
            category=category,
            owner=owner,
            user_id=user_id
        )

    # Apply multi-value filters in Python if needed
    if filter_document_ids:
        rows = [r for r in rows if r[1] in filter_document_ids]  # r[1] is document_id

    if filter_categories:
        rows = [r for r in rows if r[6] in filter_categories]  # r[6] is category

    # Note: filter_tags is not applied in sparse search because the chunks table
    # doesn't store tags directly. Tags are stored in the documents table and
    # in Pinecone metadata. Tag filtering is handled by the dense (Pinecone) path.

    if not rows:
        return []

    documents = []
    metadata_map = {}

    for row in rows:
        chunk_id = row[0]
        doc_id = row[1]
        text = row[2]
        page_number = row[3]
        filename = row[4]
        owner_val = row[5]
        category_val = row[6]

        documents.append(tokenize(text))

        metadata_map[chunk_id] = {
            "chunk_id": chunk_id,
            "document_id": doc_id,
            "text": text,
            "page_number": page_number,
            "filename": filename,
            "owner": owner_val,
            "category": category_val
        }

    bm25 = BM25Okapi(documents)

    tokenized_query = tokenize(query)

    scores = bm25.get_scores(tokenized_query)

    results = []

    for i, score in enumerate(scores):

        chunk_id = rows[i][0]

        results.append({
            "id": chunk_id,
            "score": float(score),
            "metadata": metadata_map[chunk_id]
        })

    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return results[:top_k]