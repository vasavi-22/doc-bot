"""
Phase 11 — RAG Pipeline with LangGraph Orchestration

This file retains the public API (query_rag, query_rag_stream) for backwards
compatibility with the evaluation system and other callers. Internally it
dispatches to either the LangGraph state machine or the original linear
pipeline based on the RAG_PIPELINE_MODE feature flag.
"""

import json
import requests
from config import Config
from utils.logger import logger
from services.langfuse_service import get_langfuse
from services.langfuse_tracing import safe_span, safe_generation, end_span

GROQ_API_KEY = Config.GROQ_API_KEY

_lf_client = None


def _get_lf():
    global _lf_client
    if _lf_client is None:
        _lf_client = get_langfuse()
    return _lf_client


def _filter_sources(answer, unique_sources):
    """Only return sources that the model actually referenced in its response."""
    answer_lower = answer.lower()
    sources_used = []
    for s in unique_sources:
        fname = s.get("filename", "")
        if fname.lower() in answer_lower:
            sources_used.append(s)
        elif fname.lower().replace(".pdf", "") in answer_lower:
            sources_used.append(s)
    return sources_used


# ── Dispatch helpers ─────────────────────────────────────────────────────────

def _use_graph_mode() -> bool:
    """Check the feature flag."""
    return Config.RAG_PIPELINE_MODE == "graph"


def _run_graph_pipeline(
    question,
    chat_id=None,
    document_id=None,
    category=None,
    owner=None,
    user_id=None,
    user_role=None,
    filter_document_ids=None,
    filter_categories=None,
    filter_tags=None,
    langfuse_trace=None,
    chat_history_lc=None,
):
    """Run the LangGraph state machine."""
    from graph import create_initial_state, run_rag_pipeline as run_graph

    initial_state = create_initial_state(
        question=question,
        chat_id=chat_id,
        document_id=document_id,
        category=category,
        owner=owner,
        user_id=user_id,
        user_role=user_role or "admin",
        filter_document_ids=filter_document_ids,
        filter_categories=filter_categories,
        filter_tags=filter_tags,
        langfuse_trace=langfuse_trace,
        chat_history=chat_history_lc or [],
    )

    config = {"recursion_limit": 25}
    result = run_graph(initial_state, config)
    return result


def _run_linear_pipeline(
    question,
    chat_id=None,
    document_id=None,
    category=None,
    owner=None,
    user_id=None,
    user_role=None,
    filter_document_ids=None,
    filter_categories=None,
    filter_tags=None,
    langfuse_trace=None,
    chat_history_lc=None,
):
    """Fallback: original linear pipeline (retrieve → rerank → generate)."""
    from services.hybrid_retriever import hybrid_search
    from services.reranker import rerank

    from config import Config as Cfg
    TOP_K = Cfg.TOP_K_RESULTS
    RETRIEVAL_K = Cfg.RETRIEVAL_TOP_K

    has_active_filters = bool(filter_document_ids or filter_categories or filter_tags)

    # ── Retrieve ──
    matches = hybrid_search(
        question, top_k=RETRIEVAL_K,
        document_id=document_id, category=category, owner=owner,
        user_id=user_id, user_role=user_role,
        filter_document_ids=filter_document_ids,
        filter_categories=filter_categories,
        filter_tags=filter_tags,
    )
    scored_matches = [m for m in matches if m.get("score", 0) > 0.15]

    if not scored_matches:
        if has_active_filters:
            return {"context": "__NO_RESULTS__", "unique_sources": [], "no_results": True}
        return {"context": "", "unique_sources": [], "no_results": False, "standalone_question": question}

    # ── Rerank ──
    reranked = rerank(question, scored_matches, top_k=TOP_K)

    # ── Format context ──
    context_chunks = []
    sources = []
    for match in reranked:
        meta = match["metadata"]
        fname = meta.get("filename", "Unknown")
        page = meta.get("page_number", "N/A")
        text = meta.get("text", "")
        cat = meta.get("category", "")
        tags = meta.get("tags", [])
        entry = {"filename": fname, "page": page}
        if cat:
            entry["category"] = cat
        if tags:
            entry["tags"] = ", ".join(tags) if isinstance(tags, list) else str(tags)
        context_chunks.append(f"Document: {fname}\nPage: {page}\nCategory: {cat}\n\n{text}")
        sources.append(entry)

    context = "\n\n".join(context_chunks)[:2000]

    if has_active_filters and not sources:
        return {"context": "__NO_RESULTS__", "unique_sources": [], "no_results": True}

    seen = set()
    unique_sources = []
    for s in sources:
        key = (s["filename"], str(s.get("page", "")))
        if key not in seen:
            seen.add(key)
            unique_sources.append(s)

    return {
        "context": context,
        "unique_sources": unique_sources,
        "no_results": False,
        "standalone_question": question,
    }


# ── Public API: Non-streaming query ──────────────────────────────────────────

def query_rag(question, document_id=None, category=None, owner=None, user_id=None,
              filter_document_ids=None, filter_categories=None, filter_tags=None,
              user_role=None, langfuse_trace=None):
    """
    Non-streaming RAG query.

    Dispatches to LangGraph state machine (Phase 11) or linear pipeline
    based on RAG_PIPELINE_MODE feature flag.
    """
    try:
        if not GROQ_API_KEY:
            return {"error": "GROQ_API_KEY not set"}

        if _use_graph_mode():
            result = _run_graph_pipeline(
                question=question, document_id=document_id, category=category,
                owner=owner, user_id=user_id, user_role=user_role or "admin",
                filter_document_ids=filter_document_ids,
                filter_categories=filter_categories,
                filter_tags=filter_tags,
                langfuse_trace=langfuse_trace,
            )
        else:
            result = _run_linear_pipeline(
                question=question, document_id=document_id, category=category,
                owner=owner, user_id=user_id, user_role=user_role,
                filter_document_ids=filter_document_ids,
                filter_categories=filter_categories,
                filter_tags=filter_tags,
                langfuse_trace=langfuse_trace,
            )

        if result.get("error"):
            return {"error": result["error"]}
        if result.get("no_results"):
            return {"answer": "", "sources": [], "no_results": True}

        return {
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
        }
    except Exception as e:
        logger.error(f"RAG query error: {str(e)}")
        return {"error": f"Error: {str(e)}"}


# ── Public API: Streaming query ──────────────────────────────────────────────

def query_rag_stream(question, document_id=None, category=None, owner=None, user_id=None,
                     filter_document_ids=None, filter_categories=None, filter_tags=None,
                     user_role=None, langfuse_trace=None):
    """
    Streaming RAG query — yields SSE-formatted strings.

    Uses LangGraph (or linear fallback) for retrieval phase, then streams
    the answer from Groq for real-time token delivery.
    """
    lf = _get_lf()
    llm_span = None

    if not GROQ_API_KEY:
        yield f"data: {json.dumps({'type': 'error', 'message': 'GROQ_API_KEY not set'})}\n\n"
        return

    try:
        # ── Retrieval phase (use linear pipeline — no generation waste) ──
        result = _run_linear_pipeline(
            question=question, document_id=document_id, category=category,
            owner=owner, user_id=user_id, user_role=user_role,
            filter_document_ids=filter_document_ids,
            filter_categories=filter_categories,
            filter_tags=filter_tags,
            langfuse_trace=langfuse_trace,
        )

        if result.get("error"):
            yield f"data: {json.dumps({'type': 'error', 'message': result['error']})}\n\n"
            return

        context = result.get("context", "")
        unique_sources = result.get("unique_sources", [])
        no_results = result.get("no_results", False)

        if context == "__NO_RESULTS__" or no_results:
            yield f"data: {json.dumps({'type': 'no_results', 'filters_active': True})}\n\n"
            return

        # ── Build prompt ──
        if context.strip():
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

        # ── LangFuse: LLM generation span ──
        llm_span = safe_generation(langfuse_trace or lf, "llm-call",
            model="llama-3.3-70b-versatile",
            model_parameters={"temperature": temperature, "max_tokens": 1024},
            input={
                "system_prompt": system_prompt[:500],
                "user_message": user_content[:500],
                "question": question
            }
        )

        # Make streaming request to Groq
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                "temperature": temperature,
                "max_tokens": 1024,
                "stream": True
            },
            stream=True,
            timeout=30
        )

        if not response.ok:
            error_body = "Unknown error"
            try:
                error_body = response.json().get("error", {}).get("message", f"HTTP {response.status_code}")
            except Exception:
                error_body = f"HTTP {response.status_code}"
            logger.error(f"Groq streaming error: {error_body}")
            end_span(llm_span)
            yield f"data: {json.dumps({'type': 'error', 'message': error_body})}\n\n"
            return

        full_answer = ""
        for line in response.iter_lines():
            if not line:
                continue
            line = line.decode("utf-8")
            if not line.startswith("data: "):
                continue
            data_str = line[6:]
            if data_str == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
            except json.JSONDecodeError:
                continue
            if "choices" not in chunk or not chunk["choices"]:
                continue
            delta = chunk["choices"][0].get("delta", {})
            content = delta.get("content", "")
            if content:
                full_answer += content
                yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"

        sources_used = _filter_sources(full_answer, unique_sources)

        end_span(llm_span)
        if llm_span is not None and hasattr(llm_span, 'update'):
            try:
                llm_span.update(
                    output={"answer": full_answer[:500], "sources": sources_used},
                    usage={"input": 0, "output": 0, "unit": "TOKENS"}
                )
            except:
                pass

        yield f"data: {json.dumps({'type': 'sources', 'sources': sources_used})}\n\n"

    except Exception as e:
        end_span(llm_span)
        logger.error(f"Streaming error: {str(e)}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"