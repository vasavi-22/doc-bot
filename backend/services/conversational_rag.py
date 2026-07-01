"""
Phase 11 — Conversational RAG with LangGraph Orchestration

The public API surface remains unchanged so routes/chat.py does not need
any modifications. Behind the scenes, the linear pipeline is replaced
by a LangGraph-driven state machine.

Feature flag: Set Config.RAG_PIPELINE_MODE to "graph" (default) or "linear".
"""

import json
from langchain_core.messages import HumanMessage, AIMessage

from services.llm import get_groq_llm
from services.conversation_service import build_langchain_history
from services.langfuse_tracing import safe_span, safe_generation, end_span
from config import Config
from utils.logger import logger


# ── Dispatch helpers ─────────────────────────────────────────────────────────

def _use_graph_mode() -> bool:
    """Check the feature flag to decide which pipeline to use."""
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
    """Run the LangGraph state machine and return the result state."""
    from graph import create_initial_state, run_rag_pipeline

    initial_state = create_initial_state(
        question=question,
        chat_id=chat_id,
        document_id=document_id,
        category=category,
        owner=owner,
        user_id=user_id,
        user_role=user_role,
        filter_document_ids=filter_document_ids,
        filter_categories=filter_categories,
        filter_tags=filter_tags,
        langfuse_trace=langfuse_trace,
        chat_history=chat_history_lc or [],
    )

    config = {"recursion_limit": 25}
    result = run_rag_pipeline(initial_state, config)
    return result


# ── Main conversational RAG (non-streaming) ───────────────────────────────────

def query_conversational_rag(
    question,
    chat_id=None,
    document_id=None,
    category=None,
    owner=None,
    user_id=None,
    filter_document_ids=None,
    filter_categories=None,
    filter_tags=None,
    user_role=None,
    langfuse_trace=None
):
    """
    Full conversational RAG query.

    Uses LangGraph state machine (Phase 11) or falls back to linear pipeline
    based on the RAG_PIPELINE_MODE feature flag.

    LangGraph Flow:
    1. Load chat history
    2. Rewrite question → Retriever → Need More Search?
    3. Reranker → Generator → Validator
    4. Return answer with sources
    """
    try:
        if not Config.GROQ_API_KEY:
            return {"error": "GROQ_API_KEY not set"}

        # ── Load chat history (shared between both modes) ──
        chat_history_lc = []
        if chat_id:
            chat_history_lc = build_langchain_history(chat_id, max_messages=10)
            logger.info(f"Loaded {len(chat_history_lc)} history messages for chat {chat_id}")

        if _use_graph_mode():
            # ── Phase 11: LangGraph state machine (includes search quality
            #     check, retry, rerank, generation, and validation) ──
            result = _run_graph_pipeline(
                question=question,
                chat_id=chat_id,
                document_id=document_id,
                category=category,
                owner=owner,
                user_id=user_id,
                user_role=user_role,
                filter_document_ids=filter_document_ids,
                filter_categories=filter_categories,
                filter_tags=filter_tags,
                langfuse_trace=langfuse_trace,
                chat_history_lc=chat_history_lc,
            )

            if result.get("error"):
                return {"error": result["error"]}

            # Phase 12: Handle early abstention (insufficient evidence)
            if result.get("abstain"):
                return {
                    "answer": result.get("verification_reason", ""),
                    "sources": [],
                    "no_results": True,
                    "abstain": True,
                    "confidence": result.get("confidence", 0),
                }

            if result.get("no_results"):
                has_active_filters = bool(
                    filter_document_ids or filter_categories or filter_tags
                )
                return {
                    "answer": "",
                    "sources": [],
                    "no_results": True,
                    "filters_active": has_active_filters,
                }

            return {
                "answer": result.get("answer", ""),
                "sources": result.get("sources", []),
            }
        else:
            # ── Fallback: original linear pipeline ──
            from services.rag_pipeline import _run_linear_pipeline
            linear_result = _run_linear_pipeline(
                question=question,
                chat_id=chat_id,
                document_id=document_id,
                category=category,
                owner=owner,
                user_id=user_id,
                user_role=user_role,
                filter_document_ids=filter_document_ids,
                filter_categories=filter_categories,
                filter_tags=filter_tags,
                langfuse_trace=langfuse_trace,
                chat_history_lc=chat_history_lc,
            )

            if linear_result.get("no_results"):
                has_active_filters = bool(
                    filter_document_ids or filter_categories or filter_tags
                )
                return {
                    "answer": "",
                    "sources": [],
                    "no_results": True,
                    "filters_active": has_active_filters,
                }

            # Linear pipeline only does retrieval + reranking.
            # Generate the answer with the linear approach.
            context = linear_result.get("context", "")
            unique_sources = linear_result.get("unique_sources", [])
            standalone_question = linear_result.get("standalone_question", question)

            from services.llm import get_groq_llm_non_streaming
            from services.prompts import QA_PROMPT, GENERAL_QA_PROMPT

            llm = get_groq_llm_non_streaming(
                temperature=0.3 if context.strip() else 0.5
            )

            if context.strip():
                prompt = QA_PROMPT
                chain = prompt | llm
                gen_result = chain.invoke({
                    "chat_history": chat_history_lc,
                    "context": context,
                    "question": standalone_question,
                })
            else:
                prompt = GENERAL_QA_PROMPT
                chain = prompt | llm
                gen_result = chain.invoke({
                    "chat_history": chat_history_lc,
                    "question": standalone_question,
                })

            answer = gen_result.content.strip()
            from services.rag_pipeline import _filter_sources
            sources_used = _filter_sources(answer, unique_sources) if context.strip() else []

            return {
                "answer": answer,
                "sources": sources_used,
            }

    except Exception as e:
        logger.error(f"Conversational RAG error: {str(e)}")
        return {"error": f"Error: {str(e)}"}


# ── Streaming conversational RAG ──────────────────────────────────────────────

def query_conversational_rag_stream(
    question,
    chat_id=None,
    document_id=None,
    category=None,
    owner=None,
    user_id=None,
    filter_document_ids=None,
    filter_categories=None,
    filter_tags=None,
    user_role=None,
    langfuse_trace=None
):
    """
    Streaming conversational RAG — generator that yields SSE-formatted strings.

    Uses the LangGraph graph for retrieval + evaluation + reranking,
    then streams the answer from Groq for real-time token delivery.
    """
    gen_span = None
    if not Config.GROQ_API_KEY:
        yield f"data: {json.dumps({'type': 'error', 'message': 'GROQ_API_KEY not set'})}\n\n"
        return

    try:
        # Step 1: Load chat history
        chat_history_lc = []
        if chat_id:
            chat_history_lc = build_langchain_history(chat_id, max_messages=10)
            logger.info(f"Stream - loaded {len(chat_history_lc)} history messages for chat {chat_id}")

        # Step 2: Run retrieval prep (retrieval + reranking only — no generation)
        # Uses the linear prep pipeline to avoid wasteful LLM calls (the graph's
        # generation + validation loop is incompatible with streaming output).
        from services.rag_pipeline import _run_linear_pipeline
        result = _run_linear_pipeline(
            question=question,
            chat_id=chat_id,
            document_id=document_id,
            category=category,
            owner=owner,
            user_id=user_id,
            user_role=user_role,
            filter_document_ids=filter_document_ids,
            filter_categories=filter_categories,
            filter_tags=filter_tags,
            langfuse_trace=langfuse_trace,
            chat_history_lc=chat_history_lc,
        )

        if result.get("error"):
            yield f"data: {json.dumps({'type': 'error', 'message': result['error']})}\n\n"
            return

        # Phase 12: Handle early abstention (insufficient evidence)
        if result.get("abstain"):
            yield f"data: {json.dumps({'type': 'abstain', 'message': result.get('verification_reason', ''), 'confidence': result.get('confidence', 0)})}\n\n"
            return

        context = result.get("context", "")
        unique_sources = result.get("unique_sources", [])
        no_results = result.get("no_results", False)
        standalone_question = result.get("standalone_question", question)

        if context == "__NO_RESULTS__" or no_results:
            yield f"data: {json.dumps({'type': 'no_results', 'filters_active': True})}\n\n"
            return

        # Step 3: Stream answer from Groq via LangChain
        llm = get_groq_llm(temperature=0.3 if context.strip() else 0.5)

        gen_span = safe_generation(langfuse_trace, "llm-call",
            model="llama-3.3-70b-versatile",
            model_parameters={"temperature": 0.3 if context.strip() else 0.5, "max_tokens": 1024},
            input={
                "question": standalone_question,
                "context_length": len(context),
                "has_history": bool(chat_history_lc)
            }
        )

        if context.strip():
            from services.prompts import QA_PROMPT
            prompt = QA_PROMPT
            chain = prompt | llm
            inputs = {
                "chat_history": chat_history_lc,
                "context": context,
                "question": standalone_question,
            }
        else:
            from services.prompts import GENERAL_QA_PROMPT
            prompt = GENERAL_QA_PROMPT
            chain = prompt | llm
            inputs = {
                "chat_history": chat_history_lc,
                "question": standalone_question,
            }

        full_answer = ""
        for chunk in chain.stream(inputs):
            if chunk.content:
                full_answer += chunk.content
                yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"

        # Step 4: Filter sources
        from services.rag_pipeline import _filter_sources
        sources_used = _filter_sources(full_answer, unique_sources) if context.strip() else []

        if gen_span is not None:
            try:
                gen_span.update(output={"answer": full_answer[:500], "sources": sources_used})
            except:
                pass
        end_span(gen_span)

        yield f"data: {json.dumps({'type': 'sources', 'sources': sources_used})}\n\n"

    except Exception as e:
        end_span(gen_span)
        logger.error(f"Conversational RAG stream error: {str(e)}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
