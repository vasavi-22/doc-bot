from rank_bm25 import BM25Okapi
from database import get_chunks

def tokenize(text):
    return text.lower().split()


def sparse_search(
    query,
    top_k=10,
    document_id=None,
    category=None,
    owner=None
):

    rows = get_chunks(
        document_id=document_id,
        category=category,
        owner=owner
    )

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