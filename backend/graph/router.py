"""
Phase 12 — Multi-Agent Conditional Routing

Decision points that make the workflow agentic:
1. After retrieval → should we search again with a better query?
2. After verification → should we proceed or abstain?
3. After validation → should we regenerate the answer?

Routing logic is kept lightweight and deterministic where possible.
"""

from typing import Literal
from utils.logger import logger

from .state import RAGState

SEARCH_QUALITY_THRESHOLD = 0.3
MIN_RESULTS_THRESHOLD = 2


def need_more_search(state: RAGState) -> Literal["sufficient", "need_more"]:
    """Router: After retrieval, decide if more context is needed.

    - "sufficient": results are good enough → proceed to reranker
    - "need_more": retry with a rewritten query → go to retrieve_more
    """
    chunks = state.get("retrieved_chunks", [])
    attempts = state.get("search_attempts", 0)
    max_attempts = state.get("max_search_attempts", 2)

    if not chunks:
        return "need_more" if attempts < max_attempts else "sufficient"

    top_scores = [c.get("score", 0) for c in chunks[:3]]
    avg_score = sum(top_scores) / len(top_scores) if top_scores else 0

    if len(chunks) >= MIN_RESULTS_THRESHOLD and avg_score >= SEARCH_QUALITY_THRESHOLD:
        logger.info(f"Route: sufficient (avg_score={avg_score:.3f}, count={len(chunks)})")
        return "sufficient"
    elif attempts < max_attempts:
        logger.info(f"Route: need_more (avg_score={avg_score:.3f}, count={len(chunks)})")
        return "need_more"
    else:
        logger.info("Route: sufficient (max attempts)")
        return "sufficient"


def verification_result(state: RAGState) -> Literal["verified", "abstain"]:
    """Router: After verification, decide whether to proceed or abstain.

    Phase 12 enhancement — if evidence is insufficient, the graph
    terminates early with a safe response rather than generating
    a low-quality answer.

    - "verified": evidence is sufficient → proceed to memory manager
    - "abstain": insufficient evidence → skip to END (return early)
    """
    abstain = state.get("abstain", True)
    verified = state.get("verified", False)
    confidence = state.get("confidence", 0.0)

    if abstain or not verified:
        reason = state.get("verification_reason", "Insufficient evidence")
        logger.info(f"Route: abstain (confidence={confidence:.2f}, reason={reason[:50]})")
        return "abstain"

    logger.info(f"Route: verified (confidence={confidence:.2f})")
    return "verified"


def should_retry(state: RAGState) -> Literal["regenerate", "end"]:
    """Router: After validation, decide whether to retry generation.

    - "regenerate": answer didn't cite sources → go back to answer agent
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
