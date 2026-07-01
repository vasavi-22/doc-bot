"""
Phase 12 — Retrieval Agent

Responsibility: Retrieve candidate documents from Pinecone via hybrid search.
Wraps the existing hybrid_search service — no new logic.
No LLM required — purely search.
"""

from utils.logger import logger
from config import Config

RETRIEVAL_TOP_K = Config.RETRIEVAL_TOP_K


def retrieve_documents(
    question: str,
    document_id=None,
    category=None,
    owner=None,
    user_id=None,
    filter_document_ids=None,
    filter_categories=None,
    filter_tags=None,
    user_role=None,
) -> dict:
    """Retrieve candidate chunks via hybrid search.

    Args:
        question: The search query (already standalone/rewritten).
        All other params: metadata filters and RBAC (Phases 6, 8).

    Returns:
        dict with:
        - retrieved_chunks: list of chunk dicts (scored and thresholded)
        - match_count: int
        - scored_count: int
    """
    from services.hybrid_retriever import hybrid_search

    logger.info(f"Retrieval Agent searching: '{question[:60]}'")

    matches = hybrid_search(
        question,
        top_k=RETRIEVAL_TOP_K,
        document_id=document_id,
        category=category,
        owner=owner,
        user_id=user_id,
        filter_document_ids=filter_document_ids,
        filter_categories=filter_categories,
        filter_tags=filter_tags,
        user_role=user_role,
    )

    # Apply score threshold to filter low-quality candidates
    scored_matches = [m for m in matches if m.get("score", 0) > 0.15]

    logger.info(f"Retrieval Agent: {len(matches)} candidates, {len(scored_matches)} above threshold")

    return {
        "retrieved_chunks": scored_matches,
        "match_count": len(matches),
        "scored_count": len(scored_matches),
    }
