import json
from langchain_core.runnables import RunnablePassthrough
from langchain_core.messages import HumanMessage, AIMessage

from services.llm import get_groq_llm, get_groq_llm_non_streaming
from services.prompts import CONDENSE_QUESTION_PROMPT, QA_PROMPT, GENERAL_QA_PROMPT
from services.rag_pipeline import _retrieve_context, _filter_sources
from services.conversation_service import build_langchain_history
from config import Config
from utils.logger import logger

TOP_K_RESULTS = Config.TOP_K_RESULTS


# ── Question rewriting (history-aware) ────────────────────────────────────────

def _rewrite_question(question, chat_history_lc):
    """Rewrite a follow-up question into a standalone question using LangChain.

    If there's no chat history, returns the original question.
    If the question is already standalone, it's returned as-is.
    """
    if not chat_history_lc:
        return question

    try:
        llm = get_groq_llm_non_streaming(temperature=0.1)
        chain = CONDENSE_QUESTION_PROMPT | llm
        result = chain.invoke({
            "chat_history": chat_history_lc,
            "question": question,
        })
        rewritten = result.content.strip()
        logger.info(f"Question rewritten: '{question[:60]}' -> '{rewritten[:60]}'")
        return rewritten
    except Exception as e:
        logger.error(f"Question rewriting failed: {e}. Using original question.")
        return question


# ── Main conversational RAG (non-streaming) ───────────────────────────────────

def query_conversational_rag(
    question,
    chat_id=None,
    document_id=None,
    category=None,
    owner=None,
    user_id=None
):
    """
    Full conversational RAG query.

    Flow:
    1. Load chat history (last 10 messages via LangChain format)
    2. Rewrite the question to be standalone using history
    3. Retrieve relevant context
    4. Generate answer with history + context
    5. Filter sources
    """
    try:
        if not Config.GROQ_API_KEY:
            return {"error": "GROQ_API_KEY not set"}

        # Step 1: Load chat history
        chat_history_lc = []
        if chat_id:
            chat_history_lc = build_langchain_history(chat_id, max_messages=10)
            logger.info(f"Loaded {len(chat_history_lc)} history messages for chat {chat_id}")

        # Step 2: Rewrite question using history
        standalone_question = _rewrite_question(question, chat_history_lc)

        # Step 3: Retrieve context using the standalone question
        context, unique_sources = _retrieve_context(
            standalone_question,
            document_id=document_id,
            category=category,
            owner=owner,
            user_id=user_id
        )

        # Step 4: Generate answer with history + context
        llm = get_groq_llm_non_streaming(temperature=0.3 if context.strip() else 0.5)

        if context.strip():
            prompt = QA_PROMPT
            chain = prompt | llm
            result = chain.invoke({
                "chat_history": chat_history_lc,
                "context": context,
                "question": standalone_question,
            })
        else:
            prompt = GENERAL_QA_PROMPT
            chain = prompt | llm
            result = chain.invoke({
                "chat_history": chat_history_lc,
                "question": standalone_question,
            })

        answer = result.content.strip()

        # Step 5: Filter sources
        sources_used = _filter_sources(answer, unique_sources) if context.strip() else []

        return {
            "answer": answer,
            "sources": sources_used
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
    user_id=None
):
    """
    Streaming conversational RAG — generator that yields SSE-formatted strings.

    Flow:
    1. Load chat history
    2. Rewrite question
    3. Retrieve context
    4. Stream answer from Groq
    5. Send sources at end
    """
    if not Config.GROQ_API_KEY:
        yield f"data: {json.dumps({'type': 'error', 'message': 'GROQ_API_KEY not set'})}\n\n"
        return

    try:
        # Step 1: Load chat history
        chat_history_lc = []
        if chat_id:
            chat_history_lc = build_langchain_history(chat_id, max_messages=10)
            logger.info(f"Stream - loaded {len(chat_history_lc)} history messages for chat {chat_id}")

        # Step 2: Rewrite question
        standalone_question = _rewrite_question(question, chat_history_lc)

        # Step 3: Retrieve context
        context, unique_sources = _retrieve_context(
            standalone_question,
            document_id=document_id,
            category=category,
            owner=owner,
            user_id=user_id
        )

        # Step 4: Stream answer from Groq via LangChain
        llm = get_groq_llm(temperature=0.3 if context.strip() else 0.5)

        if context.strip():
            prompt = QA_PROMPT
            chain = prompt | llm
            inputs = {
                "chat_history": chat_history_lc,
                "context": context,
                "question": standalone_question,
            }
        else:
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

        # Step 5: Filter and send sources
        sources_used = _filter_sources(full_answer, unique_sources) if context.strip() else []
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources_used})}\n\n"

    except Exception as e:
        logger.error(f"Conversational RAG stream error: {str(e)}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
