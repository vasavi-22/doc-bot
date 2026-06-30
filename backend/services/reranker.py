from sentence_transformers import CrossEncoder
from config import Config
from utils.logger import logger

_reranker = None


def get_reranker():
    """Lazy-load the CrossEncoder reranker model (singleton)."""
    global _reranker
    if _reranker is None:
        model_name = Config.RERANKER_MODEL
        logger.info(f"Loading reranker model: {model_name}")
        _reranker = CrossEncoder(model_name, max_length=512)
        logger.info("Reranker model loaded successfully")
    return _reranker


def rerank(question, chunks, top_k=5):
    """
    Re-rank candidate chunks by relevance to the question using a CrossEncoder.

    Args:
        question: The user's question string.
        chunks: List of chunk dicts, each with at least {"id": ..., "metadata": {...}}
                where metadata must contain a "text" key.
        top_k: Number of top chunks to keep after reranking.

    Returns:
        List of chunk dicts sorted by reranker score (highest first), limited to top_k.
    """
    if not chunks:
        return []

    if len(chunks) <= top_k:
        # No need to rerank if we already have few enough
        return chunks

    model = get_reranker()

    # Build (question, chunk_text) pairs
    pairs = []
    for chunk in chunks:
        text = chunk.get("metadata", {}).get("text", "")
        pairs.append((question, text))

    # Get relevance scores from the CrossEncoder
    scores = model.predict(pairs)

    # Log original vs reranked order for debugging
    logger.info("=== Reranker: Before ===")
    for i, chunk in enumerate(chunks):
        text_preview = chunk.get("metadata", {}).get("text", "")[:80].replace("\n", " ")
        filename = chunk.get("metadata", {}).get("filename", "Unknown")
        logger.info(f"  [{i}] score={chunks[i].get('score', 0):.4f} | {filename} | {text_preview}")

    # Attach reranker scores and sort
    for i, chunk in enumerate(chunks):
        chunk["_rerank_score"] = float(scores[i])

    chunks.sort(key=lambda x: x["_rerank_score"], reverse=True)

    logger.info("=== Reranker: After ===")
    for i, chunk in enumerate(chunks[:top_k]):
        text_preview = chunk.get("metadata", {}).get("text", "")[:80].replace("\n", " ")
        filename = chunk.get("metadata", {}).get("filename", "Unknown")
        logger.info(f"  [{i}] rerank={chunk['_rerank_score']:.4f} | {filename} | {text_preview}")

    # Strip the temporary rerank score from returned chunks
    result = chunks[:top_k]
    for chunk in result:
        chunk.pop("_rerank_score", None)

    return result
