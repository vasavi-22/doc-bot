"""
Phase 12 — Query Understanding Agent

Responsibility: Understand what the user is asking before retrieval.
Determines:
- user intent (summary, comparison, follow-up, factual)
- keywords for retrieval
- whether conversational memory is needed
- whether the question refers to previous messages

Reuses the existing intent_classifier service.
"""

import re
import json
import requests
from typing import Optional

from config import Config
from utils.logger import logger

# ─── Intent types ────────────────────────────────────────────────────────────

INTENT_UNKNOWN = "unknown"
INTENT_SUMMARY = "summary"
INTENT_COMPARISON = "comparison"
INTENT_FOLLOW_UP = "follow_up"
INTENT_FACTUAL = "factual"
INTENT_GENERAL = "general_conversation"

# Pattern-based intent detection (fast path, no LLM call)
_COMPARISON_PATTERNS = [
    re.compile(r"\bcompare\b", re.IGNORECASE),
    re.compile(r"\bdifference\s+(between|among)\b", re.IGNORECASE),
    re.compile(r"\bversus\b|\bvs\b", re.IGNORECASE),
    re.compile(r"\bcontrast\b", re.IGNORECASE),
    re.compile(r"\bwhich\s+is\s+(better|worse|different)\b", re.IGNORECASE),
]

_SUMMARY_PATTERNS = [
    re.compile(r"\bsummarize\b|\bsummary\b", re.IGNORECASE),
    re.compile(r"\bgive\s+me\s+(a\s+)?(brief\s+)?overview\b", re.IGNORECASE),
    re.compile(r"\bwhat'?s?\s+this\s+(document|file|pdf)\s+about\b", re.IGNORECASE),
    re.compile(r"\btell\s+me\s+about\s+this\s+(document|file|pdf)\b", re.IGNORECASE),
]

_FOLLOW_UP_PATTERNS = [
    re.compile(r"\b(what\s+about|how\s+about|and\s+|tell\s+me\s+more)\b", re.IGNORECASE),
    re.compile(r"^(can\s+you\s+)?(elaborate|expand|clarify|explain\s+further)\b", re.IGNORECASE),
    re.compile(r"\bpage\s+\d+\b", re.IGNORECASE),  # "What about page 18?"
    re.compile(r"^(it|that|this|they|he|she)\s", re.IGNORECASE),  # pronoun-starting
]


def _detect_intent_pattern(question: str) -> Optional[str]:
    """Fast pattern-based intent detection (no LLM call)."""
    text = question.strip()
    for pat in _COMPARISON_PATTERNS:
        if pat.search(text):
            return INTENT_COMPARISON
    for pat in _SUMMARY_PATTERNS:
        if pat.search(text):
            return INTENT_SUMMARY
    for pat in _FOLLOW_UP_PATTERNS:
        if pat.search(text):
            return INTENT_FOLLOW_UP
    return None


def _llm_intent_analysis(question: str, chat_history_exists: bool) -> dict:
    """Use LLM for deeper intent analysis when patterns don't match."""
    groq_api_key = Config.GROQ_API_KEY
    if not groq_api_key:
        return {"intent": INTENT_FACTUAL, "keywords": question, "needs_history": False}

    prompt = f"""\
You are a query understanding agent for a document Q&A system.
Analyze this user question and return a JSON object.

Question: "{question}"
Has chat history: {chat_history_exists}

Return ONLY valid JSON with these fields:
{{
  "intent": "summary" | "comparison" | "follow_up" | "factual",
  "keywords": "extracted key search terms (comma-separated)",
  "needs_history": true|false,
  "is_follow_up": true|false
}}

Rules:
- "summary": user wants a summary/overview of a document
- "comparison": user wants to compare two or more things
- "follow_up": user refers to previous context (pronouns, "page X", "tell me more")
- "factual": straightforward information-seeking question
- "follow_up" requires needs_history=true
- If the question starts with "it", "that", "this", "they" → is_follow_up=true
"""

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {groq_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 200,
            },
            timeout=15,
        )
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        parsed = json.loads(content)
        logger.info(f"LLM intent analysis: {parsed}")
        return parsed
    except Exception as e:
        logger.warning(f"LLM intent analysis failed: {e}")
        return {"intent": INTENT_FACTUAL, "keywords": question, "needs_history": False}


def analyze_query(question: str, has_chat_history: bool = False) -> dict:
    """Analyze the user's question and return structured understanding.

    Returns:
        dict with keys:
        - intent: str (summary/comparison/follow_up/factual/general_conversation)
        - keywords: str (extracted search terms)
        - needs_history: bool (whether conversational memory is needed)
        - is_follow_up: bool (whether question refers to previous messages)
    """
    # Stage 1: Pattern-based detection
    pattern_intent = _detect_intent_pattern(question)
    if pattern_intent:
        logger.info(f"Pattern detected intent: {pattern_intent} for '{question[:60]}'")
        return {
            "intent": pattern_intent,
            "keywords": question,
            "needs_history": pattern_intent == INTENT_FOLLOW_UP or has_chat_history,
            "is_follow_up": pattern_intent == INTENT_FOLLOW_UP,
        }

    # Stage 2: LLM analysis for complex queries
    analysis = _llm_intent_analysis(question, has_chat_history)
    return {
        "intent": analysis.get("intent", INTENT_FACTUAL),
        "keywords": analysis.get("keywords", question),
        "needs_history": analysis.get("needs_history", has_chat_history),
        "is_follow_up": analysis.get("is_follow_up", False),
    }
