import json
from rank_bm25 import BM25Okapi
from database import get_chunks, get_connection

def tokenize(text):
    return text.lower().split()


def _get_allowed_document_ids(user_role):
    """Get document IDs that the given role can access.
    
    For non-admin users, this filters documents by their allowed_roles field.
    Admins see everything, so this returns None for admin.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT document_id, allowed_roles FROM documents WHERE allowed_roles IS NOT NULL"
        )
        rows = cursor.fetchall()
        conn.close()
        
        allowed_ids = []
        for doc_id, roles_str in rows:
            try:
                roles = json.loads(roles_str) if roles_str else []
                if user_role in roles:
                    allowed_ids.append(doc_id)
            except (json.JSONDecodeError, TypeError):
                # If parsing fails, allow by default
                allowed_ids.append(doc_id)
        return allowed_ids
    except Exception:
        conn.close()
        return None


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
    if user_role and user_role != "admin":
        # Non-admin: don't filter by user_id (role filter provides access control)
        # Fetch all chunks and filter by allowed_roles after
        rows = get_chunks(
            document_id=document_id,
            category=category,
            owner=owner,
            user_id=None
        )
        # Then filter by role-accessible documents
        allowed_doc_ids = _get_allowed_document_ids(user_role)
        if allowed_doc_ids is not None:
            rows = [r for r in rows if r[1] in allowed_doc_ids]
    else:
        # Admin or no role: use original user_id filter
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