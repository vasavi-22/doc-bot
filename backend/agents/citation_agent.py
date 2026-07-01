"""
Phase 12 — Citation Agent

Responsibility: Build formatted references from the chunks actually used.
- Inspects the chunks referenced in the answer
- Removes duplicates
- Sorts references
- Formats citations consistently

Keeps citations separate from generation for clean maintainability.
"""

from typing import List
from utils.logger import logger


def build_citations(answer: str, unique_sources: List[dict]) -> List[dict]:
    """Build a clean, deduplicated citation list from sources referenced in the answer.

    Args:
        answer: The generated answer text (checked for source references).
        unique_sources: All unique source entries from the Reranker Agent.

    Returns:
        List of citation dicts, each with:
        - filename: str
        - page: str or int
        - category: str (optional)
        - tags: str (optional)
        Sorted alphabetically by filename.
    """
    if not answer or not unique_sources:
        return []

    answer_lower = answer.lower()
    citations = []

    for source in unique_sources:
        fname = source.get("filename", "")
        if not fname:
            continue

        # Check if the answer actually references this source
        if fname.lower() in answer_lower or fname.lower().replace(".pdf", "") in answer_lower:
            citation = {"filename": fname, "page": source.get("page", "N/A")}
            if source.get("category"):
                citation["category"] = source["category"]
            if source.get("tags"):
                citation["tags"] = source["tags"]
            citations.append(citation)

    # Deduplicate by (filename, page)
    seen = set()
    unique_citations = []
    for c in citations:
        key = (c["filename"], str(c.get("page", "")))
        if key not in seen:
            seen.add(key)
            unique_citations.append(c)

    # Sort alphabetically by filename
    unique_citations.sort(key=lambda c: c["filename"].lower())

    logger.info(f"Citation Agent: built {len(unique_citations)} citations from {len(unique_sources)} sources")
    return unique_citations


def format_citations_markdown(citations: List[dict]) -> str:
    """Format citations as a markdown reference list for display purposes."""
    if not citations:
        return ""

    lines = ["\n\n**Sources:**"]
    for c in citations:
        page_info = f" (Page {c['page']})" if c.get("page") and c["page"] != "N/A" else ""
        lines.append(f"- {c['filename']}{page_info}")
    return "\n".join(lines)
