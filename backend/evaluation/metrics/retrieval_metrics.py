"""Retrieval evaluation metrics: Recall@K, Precision@K, MRR, Hit Rate.

All metrics compare retrieved chunk document_ids against ground-truth
expected_document filenames from the evaluation dataset.
"""

import logging

logger = logging.getLogger(__name__)


def _normalise_filename(name):
    """Normalise a filename for comparison (lowercase, strip extension, strip path)."""
    import os
    name = str(name).lower().strip()
    name = os.path.basename(name)
    name = name.replace(".pdf", "").replace(".txt", "").replace(".docx", "")
    return name


def _get_retrieved_filenames(retrieved_chunks):
    """Extract normalised filenames from retrieved chunk metadata."""
    filenames = []
    for chunk in retrieved_chunks:
        meta = chunk.get("metadata", {})
        fname = meta.get("filename", "")
        if fname:
            filenames.append(_normalise_filename(fname))
    return filenames


def _is_relevant(retrieved_filename, expected_documents):
    """Check if a retrieved filename matches any expected document."""
    norm = _normalise_filename(retrieved_filename)
    for expected in expected_documents:
        if norm == _normalise_filename(expected):
            return True
        # Also check if the normalised name is a substring match
        if norm and expected and (norm in _normalise_filename(expected) or _normalise_filename(expected) in norm):
            return True
    return False


def recall_at_k(retrieved_chunks, expected_documents, k):
    """Recall@K: fraction of ground-truth documents retrieved in top K.

    Args:
        retrieved_chunks: List of chunk dicts sorted by relevance (highest first).
        expected_documents: List of expected document filenames.
        k: Number of top chunks to consider.

    Returns:
        float: Recall score between 0 and 1.
    """
    if not expected_documents:
        return 1.0  # No expected docs = trivially satisfied

    top_k = retrieved_chunks[:k]
    retrieved_fnames = _get_retrieved_filenames(top_k)

    found = 0
    for expected in expected_documents:
        for retrieved in retrieved_fnames:
            if _is_relevant(retrieved, [expected]):
                found += 1
                break

    return found / len(expected_documents)


def precision_at_k(retrieved_chunks, expected_documents, k):
    """Precision@K: fraction of top-K retrieved chunks that are relevant.

    Args:
        retrieved_chunks: List of chunk dicts sorted by relevance.
        expected_documents: List of expected document filenames.
        k: Number of top chunks to consider.

    Returns:
        float: Precision score between 0 and 1.
    """
    if not retrieved_chunks or k == 0:
        return 0.0

    top_k = retrieved_chunks[:k]
    retrieved_fnames = _get_retrieved_filenames(top_k)

    if not retrieved_fnames:
        return 0.0

    relevant_count = sum(1 for fname in retrieved_fnames if _is_relevant(fname, expected_documents))
    return relevant_count / len(retrieved_fnames)


def mean_reciprocal_rank(retrieved_chunks, expected_documents):
    """MRR: Mean Reciprocal Rank — 1/rank of first relevant document.

    If no relevant document is found, contribution is 0.

    Args:
        retrieved_chunks: List of chunk dicts sorted by relevance.
        expected_documents: List of expected document filenames.

    Returns:
        float: MRR score between 0 and 1.
    """
    if not expected_documents:
        return 1.0

    retrieved_fnames = _get_retrieved_filenames(retrieved_chunks)

    for rank, fname in enumerate(retrieved_fnames, start=1):
        if _is_relevant(fname, expected_documents):
            return 1.0 / rank

    return 0.0


def hit_rate(retrieved_chunks, expected_documents):
    """Hit Rate: whether at least one relevant document was retrieved (anywhere in the list).

    Args:
        retrieved_chunks: List of chunk dicts sorted by relevance.
        expected_documents: List of expected document filenames.

    Returns:
        float: 1.0 if at least one relevant doc found, 0.0 otherwise.
    """
    if not expected_documents:
        return 1.0

    retrieved_fnames = _get_retrieved_filenames(retrieved_chunks)

    for fname in retrieved_fnames:
        if _is_relevant(fname, expected_documents):
            return 1.0

    return 0.0


def evaluate_retrieval(retrieved_chunks, expected_documents):
    """Run all retrieval metrics and return a dict of scores.

    Args:
        retrieved_chunks: Full list of retrieved chunk dicts (pre-reranking).
        expected_documents: List of expected document filenames.

    Returns:
        dict: { "recall@1": ..., "recall@3": ..., "recall@5": ..., "recall@10": ...,
                "precision@5": ..., "mrr": ..., "hit_rate": ... }
    """
    ks = [1, 3, 5, 10]
    scores = {}

    for k in ks:
        scores[f"recall@{k}"] = round(recall_at_k(retrieved_chunks, expected_documents, k), 4)
        if k <= 5:
            scores[f"precision@{k}"] = round(precision_at_k(retrieved_chunks, expected_documents, k), 4)

    scores["mrr"] = round(mean_reciprocal_rank(retrieved_chunks, expected_documents), 4)
    scores["hit_rate"] = round(hit_rate(retrieved_chunks, expected_documents), 4)

    return scores
