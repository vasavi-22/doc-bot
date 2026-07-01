"""
Phase 12 — Reranker Agent

Responsibility: Rerank retrieved chunks using cross-encoder, remove weak chunks,
keep top-k. Wraps the existing reranker service — no new logic.
"""

from utils.logger import logger
from config import Config

TOP_K_RESULTS = Config.TOP_K_RESULTS


def rerank_documents(question: str, chunks: list) -> dict:
    """Rerank candidate chunks by relevance to the question.

    Args:
        question: The user's query.
        chunks: List of raw chunk dicts from the Retrieval Agent.

    Returns:
        dict with:
        - reranked_chunks: list of reranked chunk dicts (top-k)
        - reranked_count: int
        - lowest_score: float
        - highest_score: float
    """
    if not chunks:
        logger.info("Reranker Agent: no chunks to rerank")
        return {"reranked_chunks": [], "reranked_count": 0, "lowest_score": 0, "highest_score": 0}

    from services.reranker import rerank

    logger.info(f"Reranker Agent: reranking {len(chunks)} candidate chunks")
    reranked = rerank(question, chunks, top_k=TOP_K_RESULTS)

    scores = [c.get("_rerank_score", c.get("score", 0)) for c in reranked]
    return {
        "reranked_chunks": reranked,
        "reranked_count": len(reranked),
        "lowest_score": min(scores) if scores else 0,
        "highest_score": max(scores) if scores else 0,
    }
