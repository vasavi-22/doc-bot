"""
Phase 11 — Graph Nodes

Each node wraps existing business logic from services/ into a function
that reads from the shared state and returns only the fields it updates.

Nodes are designed to be:
- Thin: delegate to existing service functions
- Testable: pure functions of state → dict
- Observable: each node can be individually traced with LangFuse
"""

"""
Phase 11 — LangGraph Node Implementations

Each node wraps existing business logic from services/ into a function
that reads from the shared state and returns only the fields it updates.

Uses lazy imports to avoid triggering service-level side effects
(e.g., Pinecone client initialization) at module load time.
"""

import requests

from config import Config
from utils.logger import logger
from services.langfuse_tracing import safe_span, safe_generation, end_span

from .state import RAGState

TOP_K_RESULTS = Config.TOP_K_RESULTS
RETRIEVAL_TOP_K = Config.RETRIEVAL_TOP_K


# ─── Node: Question Re-writer ────────────────────────────────────────────────

def rewrite_question(state: RAGState) -> dict:
    """Node: Rewrite the question using chat history for context.

    If there's no chat history, the original question is used as-is.
    This preserves conversational context (Phase 5).
    """
    from services.llm import get_groq_llm_non_streaming
    from services.prompts import CONDENSE_QUESTION_PROMPT

    chat_history = state.get("chat_history", [])
    question = state["question"]

    if not chat_history:
        logger.info("No chat history — using original question as-is")
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
        logger.error(f"Question rewriting failed: {e}. Using original question.")
        return {"standalone_question": question}


# ─── Node: Retriever ─────────────────────────────────────────────────────────

def retriever(state: RAGState) -> dict:
    """Node: Retrieve candidate chunks via hybrid search.

    Uses the standalone question (already rewritten for history).
    Applies metadata filters (Phase 6) and RBAC (Phase 8).
    Instruments with LangFuse at the node level (Phase 10).
    """
    from services.hybrid_retriever import hybrid_search

    trace = state.get("langfuse_trace")

    # LangFuse: Retrieval span (node-level tracing)
    ret_span = _make_span(trace, "retrieval", {
        "question": state["standalone_question"],
        "attempt": state["search_attempts"] + 1,
        "filters": {
            "document_ids": state.get("filter_document_ids"),
            "categories": state.get("filter_categories"),
            "tags": state.get("filter_tags"),
        }
    })

    try:
        question = state["standalone_question"]
        search_attempts = state["search_attempts"] + 1

        logger.info(f"Search attempt {search_attempts}/{state['max_search_attempts']}: '{question[:60]}'")

        matches = hybrid_search(
            question,
            top_k=RETRIEVAL_TOP_K,
            document_id=state.get("document_id"),
            category=state.get("category"),
            owner=state.get("owner"),
            user_id=state.get("user_id"),
            filter_document_ids=state.get("filter_document_ids"),
            filter_categories=state.get("filter_categories"),
            filter_tags=state.get("filter_tags"),
            user_role=state.get("user_role"),
        )

        # Apply score threshold to filter low-quality candidates
        scored_matches = [m for m in matches if m.get("score", 0) > 0.15]

        logger.info(f"Retrieved {len(matches)} candidates, {len(scored_matches)} above threshold")

        _end_span(ret_span)
        if ret_span is not None and not isinstance(ret_span, type(None)):
            try:
                ret_span.update(output={
                    "matches_count": len(matches),
                    "scored_count": len(scored_matches),
                })
            except Exception:
                pass

        return {
            "retrieved_chunks": scored_matches,
            "search_attempts": search_attempts,
        }
    except Exception as e:
        _end_span(ret_span)
        logger.error(f"Retrieval error: {e}")
        return {
            "retrieved_chunks": [],
            "search_attempts": state["search_attempts"] + 1,
            "error": str(e),
        }


# ─── Node: Additional Retrieval (query rewrite) ──────────────────────────────

def retrieve_more(state: RAGState) -> dict:
    """Node: Rewrite the search query for better results.

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
        logger.error(f"Query rewrite failed: {e}. Using original.")
        return {"standalone_question": original}


# ─── Node: Reranker ──────────────────────────────────────────────────────────

def reranker(state: RAGState) -> dict:
    """Node: Rerank retrieved chunks and format context for generation.

    Uses the existing CrossEncoder reranker (Phase 7).
    Handles the no-results case and deduplicates sources.
    """
    from services.reranker import rerank

    chunks = state.get("retrieved_chunks", [])
    question = state["standalone_question"]
    has_active_filters = bool(
        state.get("filter_document_ids") or
        state.get("filter_categories") or
        state.get("filter_tags")
    )

    # LangFuse: Reranking span
    trace = state.get("langfuse_trace")
    rera_span = _make_span(trace, "reranking", {
        "num_chunks": len(chunks),
        "question": question[:100],
    })

    # No chunks → no results
    if not chunks:
        _end_span(rera_span)
        if has_active_filters:
            return {"context": "__NO_RESULTS__", "unique_sources": [], "no_results": True}
        return {"context": "", "unique_sources": [], "no_results": False}

    # Rerank with cross-encoder
    logger.info(f"Reranking {len(chunks)} candidate chunks")
    reranked = rerank(question, chunks, top_k=TOP_K_RESULTS)

    # Build formatted context and sources
    context_chunks = []
    sources = []

    for match in reranked:
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
            f"""
        Document: {filename}
        Page: {page_number}
        Category: {category_meta}

        {text}
        """
        )
        sources.append(source_entry)

    context = "\n\n".join(context_chunks)[:2000]

    # Handle active filters with no sources
    if has_active_filters and not sources:
        _end_span(rera_span)
        return {"context": "__NO_RESULTS__", "unique_sources": [], "no_results": True}

    # Deduplicate sources by (filename, page)
    seen = set()
    unique_sources = []
    for source in sources:
        key = (source["filename"], str(source.get("page", "")))
        if key not in seen:
            seen.add(key)
            unique_sources.append(source)

    _end_span(rera_span)
    if rera_span is not None:
        try:
            rera_span.update(output={
                "num_reranked": len(reranked),
                "num_sources": len(unique_sources),
                "context_length": len(context),
            })
        except Exception:
            pass

    return {
        "reranked_chunks": reranked,
        "context": context,
        "unique_sources": unique_sources,
    }


# ─── Node: Generator ─────────────────────────────────────────────────────────

def generator(state: RAGState) -> dict:
    """Node: Generate answer using the LLM.

    If context is available, uses RAG-style prompting (cite sources).
    If no context, uses general knowledge prompting.
    On retry, includes validation feedback to improve the answer.
    """
    trace = state.get("langfuse_trace")
    question = state["standalone_question"]
    context = state["context"]
    validation_feedback = state.get("validation_feedback", "")
    gen_attempt = state.get("generation_attempts", 0) + 1

    has_context = bool(context.strip()) and context != "__NO_RESULTS__"

    # Build system prompt based on context availability
    if has_context:
        system_prompt = """\
You are a helpful AI assistant. Respond naturally and conversationally, like ChatGPT.

Guidelines:
- Answer the question directly. No introductions, headings, or sections.
- If the provided context is relevant, use the information and MUST cite the exact source
  filename (e.g., "According to Machine_Learning.pdf..."). Never use vague references
  like "according to the provided context" or "the document says" — always name the
  specific file.
- If the context is NOT relevant or doesn't contain the answer, answer from your own
  knowledge. Do NOT mention any documents, sources, or filenames.
- For code questions, provide working examples in markdown code blocks with brief explanation.
- Keep it concise but thorough. Never say "I couldn't find relevant information"."""
        user_content = f"""\
Context from uploaded documents:
{context}

Question: {question}

Answer naturally. If the context above is relevant, use it and cite the EXACT source filename. If not, answer from your own knowledge — do NOT mention any documents or sources."""
        temperature = 0.3
    else:
        system_prompt = """\
You are a helpful AI assistant. Respond naturally and conversationally, like ChatGPT.

Guidelines:
- Answer the question directly and concisely. No introductions, headings, or sections.
- For code questions, provide working examples in markdown code blocks with brief explanation.
- Keep it natural. Use **bold** sparingly for emphasis only."""
        user_content = question
        temperature = 0.5

    # Add validation feedback for retries
    if validation_feedback and gen_attempt > 1:
        system_prompt += f"\n\nPrevious attempt feedback: {validation_feedback}\nPlease address this in your new response."
        temperature = 0.4

    # LangFuse: Generation span (node-level)
    gen_span = safe_generation(
        trace, "llm-call",
        model="llama-3.3-70b-versatile",
        model_parameters={"temperature": temperature, "max_tokens": 1024},
        input={
            "system_prompt_preview": system_prompt[:300],
            "question": question,
            "generation_attempt": gen_attempt,
            "has_context": has_context,
        }
    )

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {Config.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                "temperature": temperature,
                "max_tokens": 1024,
            },
            timeout=30,
        )

        data = response.json()

        if "choices" in data:
            answer = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            # Update generation span with output
            _end_span(gen_span)
            if gen_span is not None:
                try:
                    gen_span.update(
                        output={"answer_preview": answer[:200]},
                        usage={
                            "input": usage.get("prompt_tokens", 0),
                            "output": usage.get("completion_tokens", 0),
                            "unit": "TOKENS",
                        }
                    )
                except Exception:
                    pass

            return {
                "answer": answer,
                "generation_attempts": gen_attempt,
                "is_valid": False,  # Always False until validated
            }
        elif "error" in data:
            _end_span(gen_span)
            return {
                "error": f"Groq API Error: {data['error']['message']}",
                "generation_attempts": gen_attempt,
            }
        else:
            _end_span(gen_span)
            return {"error": "Unexpected API response", "generation_attempts": gen_attempt}
    except Exception as e:
        _end_span(gen_span)
        logger.error(f"Generation error: {e}")
        return {"error": str(e), "generation_attempts": gen_attempt}


# ─── Node: Validator ─────────────────────────────────────────────────────────

def validator(state: RAGState) -> dict:
    """Node: Validate the generated answer.

    Checks if the answer properly cites sources from the context.
    If not, provides feedback for a single retry.
    After max retries, accepts the answer as-is.
    """
    answer = state.get("answer", "")
    unique_sources = state.get("unique_sources", [])
    context = state.get("context", "")

    has_context = bool(context.strip()) and context != "__NO_RESULTS__"

    # LangFuse: Validation span
    trace = state.get("langfuse_trace")
    val_span = _make_span(trace, "validation", {
        "has_context": has_context,
        "num_sources": len(unique_sources),
        "generation_attempt": state.get("generation_attempts", 1),
    })

    try:
        if not has_context or not unique_sources:
            # No context to validate against — always valid
            answer_sources = _filter_sources(answer, unique_sources) if unique_sources else []
            _end_span(val_span)
            return {"is_valid": True, "sources": answer_sources, "validation_feedback": ""}

        # Check if answer references any sources
        sources_used = _filter_sources(answer, unique_sources)

        if sources_used:
            _end_span(val_span)
            return {"is_valid": True, "sources": sources_used, "validation_feedback": ""}

        # No sources cited — decide retry (max 1 retry per spec: Step 10)
        gen_attempts = state.get("generation_attempts", 1)
        max_gen = state.get("max_generation_attempts", 2)

        if gen_attempts < max_gen:
            feedback = (
                "The previous answer did not cite any source filenames from the "
                "provided context. Please cite the EXACT source filename "
                "(e.g., 'According to document.pdf...') when using information "
                "from the context."
            )
            logger.info(f"Validation failed (attempt {gen_attempts}/{max_gen}): no source citations")
            _end_span(val_span)
            return {"is_valid": False, "sources": [], "validation_feedback": feedback}

        # Max retries reached — accept as-is but no sources
        logger.info(f"Max generation attempts reached — accepting answer without sources")
        _end_span(val_span)
        return {"is_valid": True, "sources": [], "validation_feedback": "Max retries reached"}

    except Exception as e:
        _end_span(val_span)
        logger.error(f"Validation error: {e}")
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
    """Safely create a LangFuse span from a trace or client."""
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
