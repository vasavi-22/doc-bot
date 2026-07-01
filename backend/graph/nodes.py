"""
Phase 12 — Multi-Agent Node Implementations

Each node wraps a specialized agent from agents/ into a function
that reads from the shared state and returns only the fields it updates.

Architecture:
  Query Agent → Retrieval Agent → Metadata Filter → Reranker Agent
  → Verification Agent → Memory Manager → Answer Agent → Citation Agent

Uses lazy imports to avoid triggering service-level side effects
at module load time.
"""

import requests

from config import Config
from utils.logger import logger
from services.langfuse_tracing import safe_span, safe_generation, end_span

from .state import RAGState

TOP_K_RESULTS = Config.TOP_K_RESULTS
RETRIEVAL_TOP_K = Config.RETRIEVAL_TOP_K


# ─── Agent: Query Understanding Agent ─────────────────────────────────────---

def query_agent(state: RAGState) -> dict:
    """Agent: Understand what the user is asking before retrieval.

    Determines intent (summary/comparison/follow_up/factual),
    extracts keywords, and detects follow-up references.
    """
    from agents.query_agent import analyze_query

    trace = state.get("langfuse_trace")
    span = _make_span(trace, "query_agent", {
        "question": state["question"][:100],
        "has_history": bool(state.get("chat_history")),
    })

    question = state["question"]
    has_history = bool(state.get("chat_history"))

    analysis = analyze_query(question, has_chat_history=has_history)

    _end_span(span)
    if span is not None:
        try:
            span.update(output=analysis)
        except Exception:
            pass

    return {
        "intent": analysis.get("intent", "factual"),
        "query_keywords": analysis.get("keywords", question),
        "needs_history": analysis.get("needs_history", has_history),
        "is_follow_up": analysis.get("is_follow_up", False),
    }


# ─── Agent: Question Rewriter (uses history when needed) ─────────────────────

def question_rewriter(state: RAGState) -> dict:
    """Agent: Rewrite the question using chat history for context.

    Only runs when needs_history=True (set by the Query Agent).
    """
    from services.llm import get_groq_llm_non_streaming
    from services.prompts import CONDENSE_QUESTION_PROMPT

    chat_history = state.get("chat_history", [])
    question = state["question"]
    needs_history = state.get("needs_history", False)

    if not chat_history or not needs_history:
        return {"standalone_question": question}

    try:
        llm = get_groq_llm_non_streaming(temperature=0.1)
        chain = CONDENSE_QUESTION_PROMPT | llm
        result = chain.invoke({
            "chat_history": chat_history,
            "question": question,
        })
        rewritten = result.content.strip()
        logger.info(f"Question rewritten: '{question[:60]}' -> '{rewritten[:60]}'")
        return {"standalone_question": rewritten}
    except Exception as e:
        logger.error(f"Question rewriting failed: {e}")
        return {"standalone_question": question}


# ─── Agent: Retrieval Agent ──────────────────────────────────────────────────

def retrieval_agent(state: RAGState) -> dict:
    """Agent: Retrieve candidate documents from Pinecone via hybrid search.

    Wraps the existing hybrid_search service. No LLM required.
    Uses the standalone question (already rewritten for history).
    Applies metadata filters (Phase 6) and RBAC (Phase 8).
    """
    from agents.retrieval_agent import retrieve_documents

    trace = state.get("langfuse_trace")
    question = state["standalone_question"]
    search_attempts = state["search_attempts"] + 1

    span = _make_span(trace, "retrieval_agent", {
        "question": question[:100],
        "attempt": search_attempts,
        "intent": state.get("intent"),
        "filters": {
            "document_ids": state.get("filter_document_ids"),
            "categories": state.get("filter_categories"),
            "tags": state.get("filter_tags"),
        }
    })

    try:
        result = retrieve_documents(
            question=question,
            document_id=state.get("document_id"),
            category=state.get("category"),
            owner=state.get("owner"),
            user_id=state.get("user_id"),
            filter_document_ids=state.get("filter_document_ids"),
            filter_categories=state.get("filter_categories"),
            filter_tags=state.get("filter_tags"),
            user_role=state.get("user_role"),
        )

        _end_span(span)
        if span is not None:
            try:
                span.update(output={
                    "match_count": result.get("match_count", 0),
                    "scored_count": result.get("scored_count", 0),
                })
            except Exception:
                pass

        return {
            "retrieved_chunks": result.get("retrieved_chunks", []),
            "match_count": result.get("match_count", 0),
            "scored_count": result.get("scored_count", 0),
            "search_attempts": search_attempts,
        }
    except Exception as e:
        _end_span(span)
        logger.error(f"Retrieval Agent error: {e}")
        return {
            "retrieved_chunks": [],
            "match_count": 0,
            "scored_count": 0,
            "search_attempts": search_attempts,
            "error": str(e),
        }


# ─── Agent: Additional Retrieval (query rewrite) ─────────────────────────────

def retrieve_more(state: RAGState) -> dict:
    """Agent: Rewrite the search query for better results.

    Called when the router decides search quality is insufficient.
    Uses LLM to create a more specific / reformulated query.
    """
    from services.llm import get_groq_llm_non_streaming

    original = state["standalone_question"]

    try:
        llm = get_groq_llm_non_streaming(temperature=0.3)
        prompt = f"""\
You are helping improve a search query for a document retrieval system.
The original query returned poor or insufficient results.

Original query: "{original}"

Rewrite this query to be more specific, using different keywords or synonyms
that might match the content better. Focus on making it more searchable.
Return ONLY the rewritten query, nothing else."""

        result = llm.invoke(prompt)
        rewritten = result.content.strip().strip('"\'')
        logger.info(f"Search query rewritten: '{original[:60]}' -> '{rewritten[:60]}'")
        return {"standalone_question": rewritten}
    except Exception as e:
        logger.error(f"Query rewrite failed: {e}")
        return {"standalone_question": original}


# ─── Agent: Metadata Filter ──────────────────────────────────────────────────

def metadata_filter(state: RAGState) -> dict:
    """Agent: Apply metadata filters to retrieved chunks.

    Independent node that filters chunks based on metadata criteria.
    Kept separate from retrieval for easier debugging and reuse.
    """
    chunks = state.get("retrieved_chunks", [])
    has_active_filters = bool(
        state.get("filter_document_ids") or
        state.get("filter_categories") or
        state.get("filter_tags")
    )

    if not chunks:
        if has_active_filters:
            return {"context": "__NO_RESULTS__", "unique_sources": [], "no_results": True}
        return {"context": "", "unique_sources": [], "no_results": False}

    # Format chunks into context and sources
    context_chunks = []
    sources = []

    for match in chunks:
        metadata = match.get("metadata", {})
        filename = metadata.get("filename", "Unknown")
        page_number = metadata.get("page_number", "N/A")
        text = metadata.get("text", "")
        category_meta = metadata.get("category", "")
        tags_meta = metadata.get("tags", [])

        source_entry = {"filename": filename, "page": page_number}
        if category_meta:
            source_entry["category"] = category_meta
        if tags_meta:
            tag_str = ", ".join(tags_meta) if isinstance(tags_meta, list) else str(tags_meta)
            source_entry["tags"] = tag_str

        context_chunks.append(
            f"Document: {filename}\nPage: {page_number}\nCategory: {category_meta}\n\n{text}"
        )
        sources.append(source_entry)

    # Still format context but note that reranker will improve ordering
    context = "\n\n".join(context_chunks)[:2000]

    if has_active_filters and not sources:
        return {"context": "__NO_RESULTS__", "unique_sources": [], "no_results": True}

    # Deduplicate sources
    seen = set()
    unique_sources = []
    for source in sources:
        key = (source["filename"], str(source.get("page", "")))
        if key not in seen:
            seen.add(key)
            unique_sources.append(source)

    return {
        "context": context,
        "unique_sources": unique_sources,
        "no_results": False,
    }


# ─── Agent: Reranker Agent ───────────────────────────────────────────────────

def reranker_agent(state: RAGState) -> dict:
    """Agent: Rerank retrieved chunks using cross-encoder, remove weak chunks.

    Wraps the existing reranker service. Replaces raw ordering with
    cross-encoder relevance scores.
    """
    from agents.reranker_agent import rerank_documents

    trace = state.get("langfuse_trace")
    question = state["standalone_question"]
    chunks = state.get("retrieved_chunks", [])

    span = _make_span(trace, "reranker_agent", {
        "num_chunks": len(chunks),
        "question": question[:100],
    })

    result = rerank_documents(question, chunks)

    _end_span(span)
    if span is not None:
        try:
            span.update(output={
                "reranked_count": result.get("reranked_count", 0),
                "highest_score": result.get("highest_score", 0),
            })
        except Exception:
            pass

    return {
        "reranked_chunks": result.get("reranked_chunks", []),
        "reranked_count": result.get("reranked_count", 0),
        "rerank_lowest_score": result.get("lowest_score", 0),
        "rerank_highest_score": result.get("highest_score", 0),
    }


# ─── Agent: Verification Agent ───────────────────────────────────────────────

def verification_agent(state: RAGState) -> dict:
    """Agent: Verify that evidence is sufficient before generating.

    NEW in Phase 12. Checks confidence, chunk count, and score quality.
    Can cause early termination with a safe abstain response.
    """
    from agents.verification_agent import verify_evidence

    trace = state.get("langfuse_trace")
    question = state["standalone_question"]
    reranked = state.get("reranked_chunks", [])

    span = _make_span(trace, "verification_agent", {
        "num_reranked": len(reranked),
        "question": question[:100],
    })

    result = verify_evidence(question, reranked)

    _end_span(span)
    if span is not None:
        try:
            span.update(output=result)
        except Exception:
            pass

    return {
        "verified": result.get("verified", False),
        "confidence": result.get("confidence", 0.0),
        "verification_reason": result.get("reason", ""),
        "abstain": result.get("abstain", True),
    }


# ─── Agent: Memory Manager ───────────────────────────────────────────────────

def memory_manager(state: RAGState) -> dict:
    """Agent: Prepare conversational context for the Answer Agent.

    Fetches recent chat history and provides relevant context
    without mixing memory logic into generation.
    """
    chat_history = state.get("chat_history", [])
    has_history = bool(chat_history)

    if not has_history:
        return {"chat_history": []}

    logger.info(f"Memory Manager: {len(chat_history)} history messages available")
    return {"chat_history": chat_history}


# ─── Agent: Answer Agent ─────────────────────────────────────────────────────

def answer_agent(state: RAGState) -> dict:
    """Agent: Generate the final answer from verified evidence.

    Does NOT search, rerank, verify, or build citations.
    Pure generation with clean prompts.
    """
    from agents.answer_agent import generate_answer

    trace = state.get("langfuse_trace")
    question = state["standalone_question"]
    context = state["context"]
    validation_feedback = state.get("validation_feedback", "")
    gen_attempt = state.get("generation_attempts", 0) + 1

    span = safe_generation(
        trace, "answer_agent",
        model="llama-3.3-70b-versatile",
        model_parameters={"temperature": 0.3, "max_tokens": 1024},
        input={
            "question": question[:100],
            "context_length": len(context),
            "generation_attempt": gen_attempt,
        }
    )

    result = generate_answer(
        question=question,
        context=context,
        chat_history=state.get("chat_history"),
        validation_feedback=validation_feedback,
        generation_attempt=gen_attempt,
    )

    if "error" in result:
        _end_span(span)
        return {"error": result["error"], "generation_attempts": gen_attempt}

    _end_span(span)
    if span is not None:
        try:
            span.update(
                output={"answer_preview": result["answer"][:200]},
                usage={"input": result.get("usage", {}).get("prompt_tokens", 0),
                       "output": result.get("usage", {}).get("completion_tokens", 0),
                       "unit": "TOKENS"}
            )
        except Exception:
            pass

    return {
        "answer": result.get("answer", ""),
        "answer_usage": result.get("usage", {}),
        "generation_attempts": gen_attempt,
        "is_valid": False,  # Always False until validated
    }


# ─── Agent: Citation Agent ────────────────────────────────────────────────────

def citation_agent(state: RAGState) -> dict:
    """Agent: Build formatted references from chunks actually referenced.

    NEW in Phase 12. Separates citation building from answer generation.
    Deduplicates, sorts, and formats references.
    """
    from agents.citation_agent import build_citations

    trace = state.get("langfuse_trace")
    answer = state.get("answer", "")
    unique_sources = state.get("unique_sources", [])

    span = _make_span(trace, "citation_agent", {
        "answer_length": len(answer),
        "available_sources": len(unique_sources),
    })

    citations = build_citations(answer, unique_sources)

    _end_span(span)
    if span is not None:
        try:
            span.update(output={"citation_count": len(citations)})
        except Exception:
            pass

    return {
        "citations": citations,
        "sources": citations,  # Backward-compat alias
    }


# ─── Agent: Validator ────────────────────────────────────────────────────────

def validator(state: RAGState) -> dict:
    """Agent: Validate the generated answer.

    Checks if the answer properly cites sources from the context.
    If not, provides feedback for a single retry.
    After max retries, accepts the answer as-is.
    """
    answer = state.get("answer", "")
    unique_sources = state.get("unique_sources", [])
    context = state.get("context", "")

    has_context = bool(context.strip()) and context != "__NO_RESULTS__"

    trace = state.get("langfuse_trace")
    span = _make_span(trace, "validator", {
        "has_context": has_context,
        "num_sources": len(unique_sources),
        "generation_attempt": state.get("generation_attempts", 1),
    })

    try:
        if not has_context or not unique_sources:
            answer_sources = _filter_sources(answer, unique_sources) if unique_sources else []
            _end_span(span)
            return {"is_valid": True, "sources": answer_sources, "validation_feedback": ""}

        sources_used = _filter_sources(answer, unique_sources)

        if sources_used:
            _end_span(span)
            return {"is_valid": True, "sources": sources_used, "validation_feedback": ""}

        gen_attempts = state.get("generation_attempts", 1)
        max_gen = state.get("max_generation_attempts", 2)

        if gen_attempts < max_gen:
            feedback = (
                "The previous answer did not cite any source filenames. "
                "Please cite the EXACT source filename "
                "(e.g., 'According to document.pdf...') when using information."
            )
            logger.info(f"Validator: failed (attempt {gen_attempts}/{max_gen})")
            _end_span(span)
            return {"is_valid": False, "sources": [], "validation_feedback": feedback}

        logger.info("Validator: max attempts reached, accepting answer")
        _end_span(span)
        return {"is_valid": True, "sources": [], "validation_feedback": ""}

    except Exception as e:
        _end_span(span)
        logger.error(f"Validator error: {e}")
        return {"is_valid": True, "sources": [], "validation_feedback": ""}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _filter_sources(answer: str, unique_sources: list) -> list:
    """Only return sources that the model actually referenced."""
    answer_lower = answer.lower()
    sources_used = []
    for s in unique_sources:
        fname = s.get("filename", "")
        if fname.lower() in answer_lower:
            sources_used.append(s)
        elif fname.lower().replace(".pdf", "") in answer_lower:
            sources_used.append(s)
    return sources_used


def _make_span(trace, name: str, data: dict):
    """Safely create a LangFuse span."""
    if trace is None:
        return None
    try:
        return safe_span(trace, name, input=data)
    except Exception:
        return None


def _end_span(span):
    """Safely end a LangFuse span."""
    if span is not None and not isinstance(span, type(None)):
        try:
            span.end()
        except Exception:
            pass
