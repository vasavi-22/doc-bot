"""
Phase 12 — Answer Agent

Responsibility: Produce the final answer from verified evidence ONLY.
Does NOT:
- search for documents
- rerank chunks
- build citations
- verify evidence

Pure generation with clean separation from other concerns.
"""

import requests
from typing import Optional

from config import Config
from utils.logger import logger


def generate_answer(
    question: str,
    context: str,
    chat_history: Optional[list] = None,
    validation_feedback: str = "",
    generation_attempt: int = 1,
) -> dict:
    """Generate an answer from verified evidence.

    Args:
        question: The user's question.
        context: Verified, reranked context string.
        chat_history: Optional LangChain message history.
        validation_feedback: Optional feedback from previous attempt.
        generation_attempt: Which attempt this is (1-based).

    Returns:
        dict with:
        - answer: str (the generated response)
        - usage: dict (token usage if available)
    """
    has_context = bool(context.strip())
    chat_history = chat_history or []

    # Build system prompt
    if has_context:
        system_prompt = """\
You are a helpful AI assistant. Your answers are based on the provided document context.

Guidelines:
- Answer the question directly. No introductions, headings, or sections.
- Use the provided context to answer. If the context doesn't contain the answer,
  say so honestly instead of making up information.
- For code questions, provide working examples in markdown code blocks.
- Keep it concise but thorough."""
        user_content = f"""\
Context from documents:
{context}

Question: {question}

Answer based on the context above. If the context is not sufficient, say so."""
        temperature = 0.3
    else:
        system_prompt = """\
You are a helpful AI assistant.

Guidelines:
- Answer the question directly and concisely.
- For code questions, provide working examples in markdown code blocks.
- Keep it natural."""
        user_content = question
        temperature = 0.5

    if validation_feedback and generation_attempt > 1:
        system_prompt += f"\n\nPrevious attempt notes: {validation_feedback}"
        temperature = 0.4

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
            return {
                "answer": data["choices"][0]["message"]["content"],
                "usage": data.get("usage", {}),
            }
        elif "error" in data:
            return {"error": f"Groq API Error: {data['error']['message']}"}
        return {"error": "Unexpected API response"}
    except Exception as e:
        logger.error(f"Answer Agent error: {e}")
        return {"error": str(e)}
