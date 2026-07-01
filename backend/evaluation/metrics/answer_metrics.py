"""Answer-level evaluation metrics.

Uses the existing sentence-transformers model to compute semantic similarity
between the expected answer and the generated answer.
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)


def _get_embedding(text):
    """Get embedding vector for text using the existing model."""
    try:
        from services.model_loader import get_model
        model = get_model()
        return model.encode(text)
    except Exception as e:
        logger.warning(f"Embedding failed for answer similarity: {e}")
        return None


def cosine_similarity(vec1, vec2):
    """Compute cosine similarity between two vectors."""
    if vec1 is None or vec2 is None:
        return 0.0
    try:
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(v1, v2) / (norm1 * norm2))
    except Exception as e:
        logger.warning(f"Cosine similarity failed: {e}")
        return 0.0


def answer_similarity(generated_answer, expected_answer):
    """Measure semantic similarity between generated and expected answer.

    Args:
        generated_answer: The LLM's generated answer text.
        expected_answer: The ground-truth expected answer text.

    Returns:
        float: Cosine similarity score between 0 and 1.
    """
    if not generated_answer or not expected_answer:
        return 0.0

    gen_emb = _get_embedding(generated_answer)
    exp_emb = _get_embedding(expected_answer)

    return round(cosine_similarity(gen_emb, exp_emb), 4)


def answer_length_ratio(generated_answer, expected_answer):
    """Measure the length ratio of generated vs expected answer.

    Useful for detecting overly verbose or too-short answers.

    Returns:
        float: Ratio clamped between 0 and 2 (values beyond are capped).
    """
    if not expected_answer:
        return 1.0

    gen_len = len(generated_answer or "")
    exp_len = len(expected_answer)

    if exp_len == 0:
        return 1.0

    ratio = gen_len / exp_len
    return round(min(max(ratio, 0.0), 2.0), 4)
