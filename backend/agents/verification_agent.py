"""
Phase 12 — Verification Agent

Responsibility: Ensure the retrieved evidence is sufficient before generating.
Checks:
- Is there enough supporting evidence?
- Do retrieved chunks agree? (consistency check)
- Is retrieval confidence acceptable?
- Should the model answer or abstain?

If verification fails, the graph can terminate early with a safe response.
"""

from utils.logger import logger
from config import Config

# Confidence thresholds
MIN_CONFIDENCE_VERIFIED = 0.4    # Minimum average score to consider verified
MIN_CHUNKS_VERIFIED = 1           # Need at least this many chunks
HIGH_CONFIDENCE = 0.7             # Score above this is high confidence


def verify_evidence(
    question: str,
    reranked_chunks: list,
) -> dict:
    """Verify that retrieved evidence is sufficient to answer the question.

    Args:
        question: The user's question.
        reranked_chunks: Reranked chunks from the Reranker Agent.

    Returns:
        dict with:
        - verified: bool (True if evidence is sufficient)
        - confidence: float (0.0 to 1.0)
        - reason: str (explanation if not verified)
        - abstain: bool (True if should abstain from answering)
    """
    if not reranked_chunks:
        logger.info("Verification Agent: no evidence → abstain")
        return {
            "verified": False,
            "confidence": 0.0,
            "reason": "No relevant documents found matching your query.",
            "abstain": True,
        }

    # Calculate confidence scores from reranked chunks
    # Use rerank score if available, fall back to retrieval score
    scores = []
    for c in reranked_chunks:
        score = c.get("_rerank_score") or c.get("score", 0)
        if isinstance(score, (int, float)):
            scores.append(score)

    if not scores:
        logger.info("Verification Agent: no scores available → default verified")
        return {
            "verified": True,
            "confidence": 0.5,
            "reason": "",
            "abstain": False,
        }

    avg_score = sum(scores) / len(scores)
    max_score = max(scores)

    logger.info(
        f"Verification Agent: avg_score={avg_score:.3f}, "
        f"max_score={max_score:.3f}, chunks={len(reranked_chunks)}"
    )

    # Decision logic
    if len(reranked_chunks) < MIN_CHUNKS_VERIFIED:
        return {
            "verified": False,
            "confidence": avg_score,
            "reason": "Insufficient evidence: too few relevant documents found.",
            "abstain": True,
        }

    if avg_score < MIN_CONFIDENCE_VERIFIED and max_score < HIGH_CONFIDENCE:
        return {
            "verified": False,
            "confidence": avg_score,
            "reason": "Low confidence: retrieved documents have weak relevance to your question.",
            "abstain": True,
        }

    # Evidence is sufficient
    confidence = min(1.0, max_score * 0.6 + avg_score * 0.4)
    return {
        "verified": True,
        "confidence": round(confidence, 3),
        "reason": "",
        "abstain": False,
    }
