import requests
# from services.vector_store import query_vectors
from services.hybrid_retriever import hybrid_search
from config import Config
from utils.logger import logger
# from services.model_loader import get_model

GROQ_API_KEY = Config.GROQ_API_KEY
TOP_K_RESULTS = Config.TOP_K_RESULTS

def query_rag(question, document_id=None, category=None, owner=None):
    try:
        if not GROQ_API_KEY:
            return "GROQ_API_KEY not set"

        # Step 1: Embedding
        # q_embedding = get_model().encode(question).tolist()
        # removed, because we did the same in hybrid search in hybrid_retriever

        logger.info("Querying Pinecone")
        # Step 2: Retrieve context

        pinecone_filter = {}
        if document_id:
            pinecone_filter["document_id"] = document_id

        if category:
            pinecone_filter["category"] = category

        if owner:
            pinecone_filter["owner"] = owner

        # result = query_vectors(q_embedding, top_k=TOP_K_RESULTS, filter=pinecone_filter if pinecone_filter else None)
        # matches = result.get("matches", [])
        matches = hybrid_search(
            question,
            top_k=TOP_K_RESULTS,
            document_id=document_id,
            category=category,
            owner=owner
        )

        # Filter relevant chunks

        context_chunks = []
        sources = []

        for match in matches:
            if match.get("score", 0) > 0.2:
                metadata = match["metadata"]

                filename = metadata.get("filename", "Unknown")
                page_number = metadata.get("page_number", "N/A")
                text = metadata.get("text", "")

                context_chunks.append(
                f"""
        Document: {filename}
        Page: {page_number}

        {text}
        """
                )

                sources.append({
                    "filename": filename,
                    "page": page_number
                })

        context = "\n\n".join(context_chunks)[:2000]

        # unique_sources = list(set(sources))
        # Remove duplicates
        seen = set()
        unique_sources = []

        for source in sources:
            key = (source["filename"], source["page"])

            if key not in seen:
                seen.add(key)
                unique_sources.append(source)

        if context.strip():
            # Context found — use it if relevant, but allow LLM knowledge as fallback
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
            # No context found — use LLM's own knowledge
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

        # Step 4: API call
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

        data = response.json()

        # Safe response handling
        if "choices" in data:

            answer = data["choices"][0]["message"]["content"]

            # Only return sources that the model actually referenced in its response
            # This prevents false citations when the model answers from its own knowledge
            answer_lower = answer.lower()
            sources_used = []
            for s in unique_sources:
                fname = s["filename"]
                # Check exact filename (e.g., "Machine_Learning.pdf")
                if fname.lower() in answer_lower:
                    sources_used.append(s)
                # Also check filename without .pdf extension (e.g., "Machine_Learning")
                elif fname.lower().replace(".pdf", "") in answer_lower:
                    sources_used.append(s)

            return {
                "answer": answer,
                "sources": sources_used
            }

        elif "error" in data:
            return f"Groq API Error: {data['error']['message']}"
        else:
            return f"Unexpected response: {data}"

    except Exception as e:
        return f"Error: {str(e)}"