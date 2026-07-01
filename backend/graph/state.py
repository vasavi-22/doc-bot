"""
Phase 11 — State Definition

Single shared state object that flows through every graph node.
Each node updates only the fields it owns, making the workflow
predictable and extensible.
"""

from typing import TypedDict, List, Optional, Any


class RAGState(TypedDict):
    """The complete state of the RAG pipeline at any point in the graph.

    ── Input parameters ──────────────────────────────────────
    These are set once at the start and read by nodes.
    Each node reads the fields it needs and writes only its own outputs.

    ── Processing state ──────────────────────────────────────
    Tracks retry counts, intermediate results, and error status.
    """

    # ── User request ──
    question: str
    chat_id: Optional[str]

    # ── Metadata filters (Phase 6) ──
    document_id: Optional[str]
    category: Optional[str]
    owner: Optional[str]
    user_id: Optional[str]
    user_role: Optional[str]
    filter_document_ids: Optional[List[str]]
    filter_categories: Optional[List[str]]
    filter_tags: Optional[List[str]]

    # ── LangFuse trace context (Phase 10) ──
    langfuse_trace: Optional[Any]

    # ── Conversational memory (Phase 5) ──
    chat_history: List

    # ── Processing state ──
    standalone_question: str      # History-aware rewritten question
    search_attempts: int           # How many times we've tried retrieving
    max_search_attempts: int       # Max search retries (default: 2)
    generation_attempts: int       # How many times we've generated
    max_generation_attempts: int   # Max generation retries (default: 2)

    # ── Retrieved + reranked chunks ──
    retrieved_chunks: List[dict]
    reranked_chunks: List[dict]

    # ── Formatted context and sources ──
    context: str                   # Formatted context string for the LLM
    unique_sources: List[dict]     # Deduplicated source entries
    no_results: bool               # True if no results found after retries

    # ── Generation results ──
    answer: str                    # The generated answer text
    sources: List[dict]            # Sources actually referenced in answer
    is_valid: bool                 # Whether the answer passed validation
    validation_feedback: str       # Feedback from validator (used for regenerate)

    # ── Error handling ──
    error: str                     # Error message if something failed


def create_initial_state(
    *,
    question: str,
    chat_id: Optional[str] = None,
    document_id: Optional[str] = None,
    category: Optional[str] = None,
    owner: Optional[str] = None,
    user_id: Optional[str] = None,
    user_role: Optional[str] = None,
    filter_document_ids: Optional[List[str]] = None,
    filter_categories: Optional[List[str]] = None,
    filter_tags: Optional[List[str]] = None,
    langfuse_trace: Optional[Any] = None,
    chat_history: Optional[List] = None,
) -> RAGState:
    """Factory: create the initial state dict for the graph."""
    return {
        # Input
        "question": question,
        "chat_id": chat_id,
        "document_id": document_id,
        "category": category,
        "owner": owner,
        "user_id": user_id,
        "user_role": user_role,
        "filter_document_ids": filter_document_ids or [],
        "filter_categories": filter_categories or [],
        "filter_tags": filter_tags or [],
        "langfuse_trace": langfuse_trace,
        "chat_history": chat_history or [],

        # Processing
        "standalone_question": question,
        "search_attempts": 0,
        "max_search_attempts": 2,
        "generation_attempts": 0,
        "max_generation_attempts": 2,

        # Results
        "retrieved_chunks": [],
        "reranked_chunks": [],
        "context": "",
        "unique_sources": [],
        "no_results": False,

        # Generation
        "answer": "",
        "sources": [],
        "is_valid": True,
        "validation_feedback": "",

        # Error
        "error": "",
    }
