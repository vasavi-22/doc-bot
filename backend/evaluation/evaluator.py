"""LLM-as-a-Judge evaluation for answer quality metrics.

Uses the existing Groq LLM to score:
  - Faithfulness: Does the answer stay true to the retrieved context?
  - Relevance: Does the answer directly address the question?
  - Groundedness: Can every claim in the answer be supported by the context?

All scores are returned on a 1-5 scale alongside a normalised 0-1 value.
"""

import json
import logging
import time

logger = logging.getLogger(__name__)

EVALUATOR_SYSTEM_PROMPT = """You are a strict evaluator of a RAG (Retrieval-Augmented Generation) system.
Your job is to score the quality of a generated answer given the original question and the retrieved context.

Score each dimension on a scale of 1 to 5:

1. **Faithfulness** — Does the answer stay factually consistent with the retrieved context?
   - 5: Perfect — every claim is directly supported by the context
   - 4: Mostly faithful — minor details not in context but nothing contradictory
   - 3: Partially faithful — some claims not in context or slightly contradictory
   - 2: Mostly unfaithful — several claims contradict or are unsupported by context
   - 1: Hallucination — answer invents facts not present in context

2. **Relevance** — Does the answer directly address the user's question?
   - 5: Perfectly relevant — directly answers the question completely
   - 4: Mostly relevant — addresses the question but includes some tangential info
   - 3: Partially relevant — touches on the question but misses important aspects
   - 2: Barely relevant — tangentially related but doesn't answer the question
   - 1: Irrelevant — does not address the question at all

3. **Groundedness** — Can every statement in the answer be traced back to the context?
   - 5: Fully grounded — every statement is explicitly supported
   - 4: Mostly grounded — most statements supported, minor unsupported claims
   - 3: Partially grounded — some statements supported, some not
   - 2: Mostly ungrounded — most claims cannot be verified in context
   - 1: Ungrounded — no claims can be verified in the context

Return ONLY valid JSON with this exact structure:
{
  "faithfulness": <1-5>,
  "faithfulness_reason": "<brief explanation>",
  "relevance": <1-5>,
  "relevance_reason": "<brief explanation>",
  "groundedness": <1-5>,
  "groundedness_reason": "<brief explanation>"
}"""


def _normalise_score(score_1_5):
    """Convert 1-5 score to 0-1 range."""
    return (score_1_5 - 1) / 4.0


def evaluate_answer(question, context, answer, llm_func=None):
    """Evaluate answer quality using LLM-as-a-Judge.

    Args:
        question: The original user question.
        context: The retrieved context text used to generate the answer.
        answer: The generated answer text.
        llm_func: Optional callable that accepts a prompt string and returns text.
                  If None, uses a minimal fallback.

    Returns:
        dict: {
            "faithfulness": <0-1>,
            "faithfulness_reason": "...",
            "relevance": <0-1>,
            "relevance_reason": "...",
            "groundedness": <0-1>,
            "groundedness_reason": "...",
            "latency_seconds": <float>
        }
    """
    start = time.time()

    # Build the evaluation prompt
    user_prompt = f"""Question: {question}

Retrieved Context:
{context[:3000]}

Generated Answer:
{answer}

Score each dimension (1-5) and provide a brief reason. Return ONLY valid JSON."""

    try:
        if llm_func:
            raw = llm_func(EVALUATOR_SYSTEM_PROMPT, user_prompt)
        else:
            # Fallback: use direct Groq API call
            import requests
            from config import Config

            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {Config.GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [
                        {"role": "system", "content": EVALUATOR_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 500
                },
                timeout=30
            )

            if not response.ok:
                logger.error(f"Evaluator API error: {response.status_code}")
                return _fallback_scores(start)

            data = response.json()
            raw = data["choices"][0]["message"]["content"]

        # Parse the JSON response
        # Try to extract JSON from the response (it might be wrapped in markdown)
        json_str = raw.strip()
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0].strip()
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0].strip()

        scores = json.loads(json_str)

        elapsed = round(time.time() - start, 3)

        return {
            "faithfulness": round(_normalise_score(scores.get("faithfulness", 3)), 4),
            "faithfulness_reason": scores.get("faithfulness_reason", ""),
            "relevance": round(_normalise_score(scores.get("relevance", 3)), 4),
            "relevance_reason": scores.get("relevance_reason", ""),
            "groundedness": round(_normalise_score(scores.get("groundedness", 3)), 4),
            "groundedness_reason": scores.get("groundedness_reason", ""),
            "latency_seconds": elapsed
        }

    except Exception as e:
        logger.error(f"Evaluator failed: {e}")
        return _fallback_scores(start)


def _fallback_scores(start_time):
    """Return neutral scores when evaluation fails."""
    elapsed = round(time.time() - start_time, 3)
    return {
        "faithfulness": 0.5,
        "faithfulness_reason": "Evaluation failed — default score",
        "relevance": 0.5,
        "relevance_reason": "Evaluation failed — default score",
        "groundedness": 0.5,
        "groundedness_reason": "Evaluation failed — default score",
        "latency_seconds": elapsed,
        "error": True
    }
