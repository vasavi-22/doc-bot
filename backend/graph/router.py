"""
Phase 11 — Conditional Routing

Decision points that make the workflow agentic:
1. After retrieval → should we search again with a better query?
2. After validation → should we regenerate the answer?

Routing logic is kept lightweight and deterministic where possible.
"""

from typing import Literal
from utils.logger import logger

from .state import RAGState

SEARCH_QUALITY_THRESHOLD = 0.3  # Minimum avg score to consider results good
MIN_RESULTS_THRESHOLD = 2        # Minimum number of results


def need_more_search(state: RAGState) -> Literal["sufficient", "need_more"]:
    """Router: After retrieval, decide if more context is needed.

    Returns the name of the next node to route to.
    - "sufficient": results are good enough → proceed to reranker
    - "need_more": retry with a rewritten query → go to retrieve_more
    """
    chunks = state.get("retrieved_chunks", [])
    attempts = state.get("search_attempts", 0)
    max_attempts = state.get("max_search_attempts", 2)

    # If no results but we haven't exhausted retries → try again
    if not chunks:
        if attempts < max_attempts:
            logger.info("Route: need_more (no results, retries left)")
            return "need_more"
        logger.info("Route: sufficient (no results, max attempts reached)")
        return "sufficient"

    # Check average score of top results
    top_scores = [c.get("score", 0) for c in chunks[:3]]
    avg_score = sum(top_scores) / len(top_scores) if top_scores else 0

    has_enough_results = len(chunks) >= MIN_RESULTS_THRESHOLD
    has_good_scores = avg_score >= SEARCH_QUALITY_THRESHOLD

    if has_enough_results and has_good_scores:
        logger.info(f"Route: sufficient (avg_score={avg_score:.3f}, count={len(chunks)})")
        return "sufficient"
    elif attempts < max_attempts:
        logger.info(f"Route: need_more (avg_score={avg_score:.3f}, count={len(chunks)})")
        return "need_more"
    else:
        logger.info(f"Route: sufficient (max attempts, best effort)")
        return "sufficient"


def should_retry(state: RAGState) -> Literal["regenerate", "end"]:
    """Router: After validation, decide whether to retry generation.

    - "regenerate": answer didn't cite sources → go back to generator
    - "end": answer is valid or max attempts reached → finish
    """
    is_valid = state.get("is_valid", True)
    gen_attempts = state.get("generation_attempts", 1)
    max_gen = state.get("max_generation_attempts", 2)

    if not is_valid and gen_attempts < max_gen:
        logger.info(f"Route: regenerate (attempt {gen_attempts}/{max_gen})")
        return "regenerate"
    logger.info(f"Route: end (valid={is_valid}, attempts={gen_attempts}/{max_gen})")
    return "end"
