"""
Phase 12 — State Definition (Multi-Agent)

Single shared state object that flows through every agent node.
Each node updates only the fields it owns, making the workflow
predictable, observable, and extensible.

Architecture follows the multi-agent pattern:
User → Query Agent → Retrieval Agent → Metadata Filter → Reranker Agent
→ Verification Agent → Memory Manager → Answer Agent → Citation Agent
"""

from typing import TypedDict, List, Optional, Any


class RAGState(TypedDict):
    """The complete state of the multi-agent RAG pipeline.

    ── Input parameters ──────────────────────────────────────
    Set once at the start. Read by multiple agents.

    ── Agent outputs ────────────────────────────────────────
    Each agent writes to its designated section. No agent reads
    from another agent's output unless explicitly designed.
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

    # ── Phase 12: Query Understanding Agent output ──
    intent: str                    # summary / comparison / follow_up / factual / general_conversation
    query_keywords: str            # Extracted key search terms
    needs_history: bool            # Whether conversational memory is needed
    is_follow_up: bool             # Whether question refers to previous messages

    # ── Processing state ──
    standalone_question: str       # History-aware rewritten question
    search_attempts: int            # How many times we've tried retrieving
    max_search_attempts: int        # Max search retries (default: 2)
    generation_attempts: int        # How many times we've generated
    max_generation_attempts: int    # Max generation retries (default: 2)

    # ── Phase 12: Retrieval Agent output ──
    retrieved_chunks: List[dict]   # Raw chunks from hybrid search
    match_count: int               # Total candidates found
    scored_count: int              # Candidates above threshold

    # ── Phase 12: Reranker Agent output ──
    reranked_chunks: List[dict]    # Cross-encoder reranked chunks
    reranked_count: int            # Number of reranked chunks
    rerank_lowest_score: float
    rerank_highest_score: float

    # ── Phase 12: Verification Agent output ──
    verified: bool                 # Whether evidence is sufficient
    confidence: float              # Confidence score (0.0 to 1.0)
    verification_reason: str       # Explanation if not verified
    abstain: bool                  # Whether to abstain from answering

    # ── Formatted context and sources ──
    context: str                   # Formatted context string for the LLM
    unique_sources: List[dict]     # Deduplicated source entries
    no_results: bool               # True if no results found after retries

    # ── Phase 12: Answer Agent output ──
    answer: str                    # The generated answer text
    answer_usage: dict             # Token usage from generation

    # ── Phase 12: Citation Agent output ──
    citations: List[dict]          # Deduplicated citations from referenced sources
    sources: List[dict]            # Backward-compat alias for sources

    # ── Validation results ──
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
    """Factory: create the initial state dict for the multi-agent graph."""
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

        # Phase 12: Query Understanding Agent
        "intent": "",
        "query_keywords": question,
        "needs_history": bool(chat_history),
        "is_follow_up": False,

        # Processing
        "standalone_question": question,
        "search_attempts": 0,
        "max_search_attempts": 2,
        "generation_attempts": 0,
        "max_generation_attempts": 2,

        # Phase 12: Retrieval Agent
        "retrieved_chunks": [],
        "match_count": 0,
        "scored_count": 0,

        # Phase 12: Reranker Agent
        "reranked_chunks": [],
        "reranked_count": 0,
        "rerank_lowest_score": 0.0,
        "rerank_highest_score": 0.0,

        # Phase 12: Verification Agent
        "verified": False,
        "confidence": 0.0,
        "verification_reason": "",
        "abstain": False,

        # Formatted context
        "context": "",
        "unique_sources": [],
        "no_results": False,

        # Phase 12: Answer Agent
        "answer": "",
        "answer_usage": {},

        # Phase 12: Citation Agent
        "citations": [],
        "sources": [],

        # Validation
        "is_valid": True,
        "validation_feedback": "",

        # Error
        "error": "",
    }
