import json
import requests
import time
# from services.vector_store import query_vectors
from services.hybrid_retriever import hybrid_search
from services.reranker import rerank
from config import Config
from utils.logger import logger
from services.langfuse_service import get_langfuse
from services.langfuse_tracing import safe_trace, safe_span, safe_generation, end_span, end_trace
# from services.model_loader import get_model

GROQ_API_KEY = Config.GROQ_API_KEY
TOP_K_RESULTS = Config.TOP_K_RESULTS
RETRIEVAL_TOP_K = Config.RETRIEVAL_TOP_K

_lf_client = None

def _get_lf():
    global _lf_client
    if _lf_client is None:
        _lf_client = get_langfuse()
    return _lf_client


def _retrieve_context(question, document_id=None, category=None, owner=None, user_id=None,
                       filter_document_ids=None, filter_categories=None, filter_tags=None,
                       user_role=None):
    """Shared retrieval logic. Returns (context, unique_sources)."""
    logger.info("Querying Pinecone (candidate generation)")

    # Check if any active metadata filters are set
    has_active_filters = bool(filter_document_ids or filter_categories or filter_tags)

    # ── Phase 7: Retrieve more candidates (RETRIEVAL_TOP_K) for reranking ──
    matches = hybrid_search(
        question,
        top_k=RETRIEVAL_TOP_K,
        document_id=document_id,
        category=category,
        owner=owner,
        user_id=user_id,
        filter_document_ids=filter_document_ids,
        filter_categories=filter_categories,
        filter_tags=filter_tags,
        user_role=user_role
    )

    # Apply score threshold to filter low-quality candidates
    scored_matches = [m for m in matches if m.get("score", 0) > 0.15]

    if not scored_matches:
        if has_active_filters:
            return "__NO_RESULTS__", []
        return "", []

    # ── Phase 7: Cross-encoder reranking ──
    logger.info(f"Reranking {len(scored_matches)} candidate chunks")
    reranked = rerank(question, scored_matches, top_k=TOP_K_RESULTS)

    context_chunks = []
    sources = []

    for match in reranked:
        metadata = match["metadata"]
        filename = metadata.get("filename", "Unknown")
        page_number = metadata.get("page_number", "N/A")
        text = metadata.get("text", "")
        category_meta = metadata.get("category", "")
        tags_meta = metadata.get("tags", [])
        # Enrich source with metadata
        source_entry = {
            "filename": filename,
            "page": page_number
        }
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

    # Handle empty results when filters are active
    if has_active_filters and not sources:
        return "__NO_RESULTS__", []

    # Deduplicate sources
    seen = set()
    unique_sources = []
    for source in sources:
        key = (source["filename"], str(source.get("page", "")))
        if key not in seen:
            seen.add(key)
            unique_sources.append(source)

    return context, unique_sources


def _build_prompt(question, context):
    """Build system prompt and user content based on whether context exists."""
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
- Keep it concise but thorough. Never say "I couldn't find relevant information".
"""
        user_content = f"""\
Context from uploaded documents:
{context}

Question: {question}

Answer naturally. If the context above is relevant, use it and cite the EXACT source filename. If not, answer from your own knowledge — do NOT mention any documents or sources.
"""
        temperature = 0.3
    else:
        system_prompt = """\
You are a helpful AI assistant. Respond naturally and conversationally, like ChatGPT.

Guidelines:
- Answer the question directly and concisely. No introductions, headings, or sections.
- For code questions, provide working examples in markdown code blocks with brief explanation.
- Keep it natural. Use **bold** sparingly for emphasis only.
- Never say "I couldn't find relevant information" — this is a general knowledge question.
"""
        user_content = question
        temperature = 0.5

    return system_prompt, user_content, temperature


def _filter_sources(answer, unique_sources):
    """Only return sources that the model actually referenced in its response."""
    answer_lower = answer.lower()
    sources_used = []
    for s in unique_sources:
        fname = s["filename"]
        if fname.lower() in answer_lower:
            sources_used.append(s)
        elif fname.lower().replace(".pdf", "") in answer_lower:
            sources_used.append(s)
    return sources_used


def query_rag(question, document_id=None, category=None, owner=None, user_id=None,
              filter_document_ids=None, filter_categories=None, filter_tags=None,
              user_role=None, langfuse_trace=None):
    """Non-streaming RAG query — returns full answer dict."""
    ret_span = llm_span = None
    lf = _get_lf()
    try:
        if not GROQ_API_KEY:
            return {"error": "GROQ_API_KEY not set"}

        # ── LangFuse: Retrieval span ──
        ret_span = safe_span(langfuse_trace or lf, "retrieval",
            input={"question": question, "filters": {
                "document_ids": filter_document_ids,
                "categories": filter_categories,
                "tags": filter_tags
            }}
        )

        context, unique_sources = _retrieve_context(
            question, document_id, category, owner, user_id,
            filter_document_ids=filter_document_ids,
            filter_categories=filter_categories,
            filter_tags=filter_tags,
            user_role=user_role
        )

        end_span(ret_span)
        if ret_span is not None and not isinstance(ret_span, type(None)):
            try: ret_span.update(output={"sources": unique_sources, "context_length": len(context)})
            except: pass

        # Handle empty results when filters are active
        if context == "__NO_RESULTS__":
            return {"answer": "", "sources": [], "no_results": True}
        system_prompt, user_content, temperature = _build_prompt(question, context)

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
        llm_start = time.time()

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
                "max_tokens": 1024
            },
            timeout=30
        )

        llm_latency = round(time.time() - llm_start, 3)
        data = response.json()

        if "choices" in data:
            answer = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            sources_used = _filter_sources(answer, unique_sources)

            # ── LangFuse: update generation with output + usage ──
            end_span(llm_span)
            if llm_span is not None:
                try:
                    llm_span.update(
                        output={"answer": answer[:500], "sources": sources_used},
                        usage={
                            "input": usage.get("prompt_tokens", 0),
                            "output": usage.get("completion_tokens", 0),
                            "unit": "TOKENS"
                        }
                    )
                except:
                    pass

            return {
                "answer": answer,
                "sources": sources_used,
                "usage": usage
            }
        elif "error" in data:
            return {"error": f"Groq API Error: {data['error']['message']}"}
        else:
            return {"error": f"Unexpected response: {data}"}

    except Exception as e:
        end_span(ret_span)
        end_span(llm_span)
        return {"error": f"Error: {str(e)}"}


def query_rag_stream(question, document_id=None, category=None, owner=None, user_id=None,
                     filter_document_ids=None, filter_categories=None, filter_tags=None,
                     user_role=None, langfuse_trace=None):
    """
    Streaming RAG query — generator that yields SSE-formatted strings.

    Yields:
        str: SSE data lines like:
            data: {"type": "token", "content": "Hello"}\n\n
            data: {"type": "sources", "sources": [...]}\n\n
            data: {"type": "error", "message": "..."}\n\n
    """
    lf = _get_lf()
    ret_span = llm_span = None

    if not GROQ_API_KEY:
        yield f"data: {json.dumps({'type': 'error', 'message': 'GROQ_API_KEY not set'})}\n\n"
        return

    try:
        # ── LangFuse: Retrieval span ──
        ret_span = safe_span(langfuse_trace or lf, "retrieval",
            input={"question": question, "filters": {
                "document_ids": filter_document_ids,
                "categories": filter_categories,
                "tags": filter_tags
            }}
        )

        context, unique_sources = _retrieve_context(
            question, document_id, category, owner, user_id,
            filter_document_ids=filter_document_ids,
            filter_categories=filter_categories,
            filter_tags=filter_tags,
            user_role=user_role
        )

        end_span(ret_span)
        if ret_span is not None and hasattr(ret_span, 'update'):
            try: ret_span.update(output={"sources": unique_sources, "context_length": len(context)})
            except: pass

        # Handle empty results when filters are active
        if context == "__NO_RESULTS__":
            yield f"data: {json.dumps({'type': 'no_results', 'filters_active': True})}\n\n"
            return

        system_prompt, user_content, temperature = _build_prompt(question, context)

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

        # Check for HTTP errors from Groq
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

        # Accumulate the full answer for source filtering
        full_answer = ""

        for line in response.iter_lines():
            if not line:
                continue

            line = line.decode("utf-8")
            if not line.startswith("data: "):
                continue

            data_str = line[6:]  # Strip "data: " prefix
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

        # After streaming completes, send sources
        sources_used = _filter_sources(full_answer, unique_sources)

        # ── LangFuse: Update generation with output ──
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
        end_span(ret_span)
        end_span(llm_span)
        logger.error(f"Streaming error: {str(e)}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"