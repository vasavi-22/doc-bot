import json
import re
import requests
from config import Config
from utils.logger import logger

INTENT_GENERAL_CONVERSATION = "GENERAL_CONVERSATION"
INTENT_DOCUMENT_QUERY = "DOCUMENT_QUERY"

CLASSIFICATION_MODEL = "llama-3.1-8b-instant"

# ─── Rule-based social chat patterns ───────────────────────────────────────────
# These catch obvious social chat quickly and reliably without an LLM call.

# Single-word social messages (case-insensitive)
SINGLE_WORD_SOCIAL = {
    "hi", "hello", "hey", "bye", "goodbye", "thanks", "thx", "ty",
    "ok", "okay", "sure", "yes", "yeah", "yep", "no", "nope", "cool",
    "nice", "great", "awesome", "perfect", "fine", "good",
}

# Two+ word social phrases (lowercase, checked as-is)
SOCIAL_PHRASES = {
    "thank you", "thanks a lot", "thank you so much", "thanks so much",
    "good morning", "good evening", "good night", "good day",
    "how are you", "how's it going", "how are you doing", "how you doing",
    "what's up", "what is up",
    "nice to meet you", "pleasure to meet you",
    "see you", "see you later", "see ya", "take care", "talk later",
    "who are you", "what can you do", "how do you work",
    "got it", "i see", "makes sense", "no problem", "you're welcome",
    "i'm good", "i am good", "i'm doing well", "i am doing well",
    "i'm doing great", "i am doing great", "doing well", "doing great",
    "doing good", "not bad", "feeling good", "feeling great",
    "appreciate it", "i appreciate it",
}

# Regex patterns for common social variants
SOCIAL_REGEX_PATTERNS = [
    re.compile(r"^(hi|hello|hey)[!.\s,]*$", re.IGNORECASE),
    re.compile(r"^(good\s+(morning|evening|night|day))[!.\s,]*$", re.IGNORECASE),
    re.compile(r"^(bye|goodbye|see\s+ya)[!.\s,]*$", re.IGNORECASE),
    re.compile(r"^(thank\s+(you|u)|thanks|thx)[!.\s,]*$", re.IGNORECASE),
    re.compile(r"^(how\s+are\s+(you|ya|u))[\s!?.,]*$", re.IGNORECASE),
    re.compile(r"^(what('s| is)\s+up)[\s!?.,]*$", re.IGNORECASE),
    re.compile(r"^(who\s+are\s+you)[\s!?.,]*$", re.IGNORECASE),
    re.compile(r"^(what\s+can\s+(you|u)\s+do)[\s!?.,]*$", re.IGNORECASE),
    re.compile(r"^(nice\s+to\s+meet\s+you)[\s!.,]*$", re.IGNORECASE),
    re.compile(r"^(ok|okay|got\s+it|sure|makes?\s+sense)[\s!.,]*$", re.IGNORECASE),
    re.compile(r"^(i'm|i\s+am)\s+(good|great|fine|doing\s+(well|great|good))[\s!.,]*$", re.IGNORECASE),
]


def _is_social_chat(message):
    """Fast rule-based check for obvious social chat. Returns True for clear social messages."""
    text = message.strip()

    # Empty or very short
    if not text:
        return True

    # Single-word check
    cleaned = text.lower().strip(" \t.,!?")
    if cleaned in SINGLE_WORD_SOCIAL:
        return True

    # Two+ word phrase check
    lower = text.lower().strip()
    if lower in SOCIAL_PHRASES:
        return True

    # Regex patterns
    for pattern in SOCIAL_REGEX_PATTERNS:
        if pattern.match(text):
            return True

    return False


# ─── LLM-based classifier (fallback for non-obvious messages) ─────────────────

CLASSIFICATION_SYSTEM_PROMPT = """\
You are an AI intent classifier for a document Q&A chatbot called DocBot.

Classify the user's message as either GENERAL_CONVERSATION or DOCUMENT_QUERY.

--- GENERAL_CONVERSATION ---
Messages that are purely social with no information-seeking intent:
- Greetings: "Hi", "Hello", "Hey", "Good morning"
- Farewells: "Bye", "Goodbye", "See you later"
- Gratitude: "Thank you", "Thanks", "Appreciate it"
- Social check-ins: "How are you?", "How's it going?"
- Assistant queries: "Who are you?", "What can you do?"
- Acknowledgments: "OK", "Got it", "Makes sense"
- Responses: "I'm good", "Doing well", "Not bad"

--- DOCUMENT_QUERY ---
Everything else, especially:
- Factual questions: "What is X?", "Who is Y?", "Define Z"
- Explanation requests: "Explain X", "Tell me about Y"
- Code requests: "Write a Python program to..."
- Document queries: "Summarize this", "What does page 5 say?"
- Compound messages: "Hi, can you summarize this?"
- Any question seeking information, knowledge, or help with a topic

--- EXAMPLES ---
"How are you?" -> GENERAL_CONVERSATION
"Who are you?" -> GENERAL_CONVERSATION
"Thank you" -> GENERAL_CONVERSATION
"What is deep learning?" -> DOCUMENT_QUERY
"Who is Shreyas Iyer?" -> DOCUMENT_QUERY
"Write a Python program" -> DOCUMENT_QUERY
"Explain quantum physics" -> DOCUMENT_QUERY
"Hi, can you summarize my document?" -> DOCUMENT_QUERY
"Give me details about shreyas iyer" -> DOCUMENT_QUERY

--- RULES ---
- If the user asks for ANY information, explanation, code, or topic knowledge -> DOCUMENT_QUERY
- Only GENERAL_CONVERSATION if the message is purely social (no information request)
- "Who are you?" and "What can you do?" are about the assistant -> GENERAL_CONVERSATION
- Greeting + question combined -> DOCUMENT_QUERY

Respond ONLY with valid JSON:

For GENERAL_CONVERSATION:
{"intent": "GENERAL_CONVERSATION", "response": "Your friendly, brief reply here."}

For DOCUMENT_QUERY:
{"intent": "DOCUMENT_QUERY"}
"""


def _classify_with_llm(message):
    """Use Groq LLM to classify a message that wasn't caught by the rule filter."""
    groq_api_key = Config.GROQ_API_KEY
    if not groq_api_key:
        logger.warning("GROQ_API_KEY not set, defaulting to DOCUMENT_QUERY")
        return INTENT_DOCUMENT_QUERY, None

    try:
        logger.info(f"LLM classifying: {message[:80]}...")

        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {groq_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": CLASSIFICATION_MODEL,
                "messages": [
                    {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
                    {"role": "user", "content": message}
                ],
                "temperature": 0.1,
                "max_tokens": 200
            },
            timeout=15
        )

        data = response.json()

        if "choices" not in data:
            logger.error(f"Groq classification error: {data.get('error', 'Unknown error')}")
            return INTENT_DOCUMENT_QUERY, None

        content = data["choices"][0]["message"]["content"].strip()

        # Parse JSON response
        parsed = json.loads(content)
        intent = parsed.get("intent", INTENT_DOCUMENT_QUERY)

        if intent == INTENT_GENERAL_CONVERSATION:
            response_text = parsed.get("response", "")
            logger.info(f"LLM classified: GENERAL_CONVERSATION")
            return INTENT_GENERAL_CONVERSATION, response_text

        logger.info(f"LLM classified: DOCUMENT_QUERY")
        return INTENT_DOCUMENT_QUERY, None

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse classification JSON: {e}")
        return INTENT_DOCUMENT_QUERY, None
    except requests.Timeout:
        logger.error("Groq classification request timed out")
        return INTENT_DOCUMENT_QUERY, None
    except requests.RequestException as e:
        logger.error(f"Groq classification request failed: {e}")
        return INTENT_DOCUMENT_QUERY, None
    except Exception as e:
        logger.error(f"Unexpected classification error: {e}")
        return INTENT_DOCUMENT_QUERY, None


# ─── Public API ────────────────────────────────────────────────────────────────

# Template responses for common social messages (used when rule-based detection
# matches, to avoid an extra LLM call just to generate a friendly response)
SOCIAL_RESPONSES = {
    "hi": "Hello! 👋 How can I help you today?",
    "hello": "Hi there! 😊 How can I assist you?",
    "hey": "Hey! 👋 What can I do for you?",
    "bye": "Goodbye! Have a great day! 😊",
    "goodbye": "See you later! Take care! 😊",
    "good morning": "Good morning! ☀️ How can I help you today?",
    "good evening": "Good evening! 🌆 What can I assist you with?",
    "good night": "Good night! Sleep well! 🌙",
    "thank you": "You're welcome! 😊 Happy to help!",
    "thanks": "You're welcome! 😊",
    "how are you": "I'm doing great, thanks for asking! How can I help you today? 😊",
    "who are you": "I'm DocBot, your AI-powered document assistant! 📄 I help answer questions about your uploaded documents and assist with general queries. What can I do for you?",
    "what can you do": "I can answer questions about your uploaded documents, explain concepts, help with code, and assist with a wide range of topics! What would you like help with? 😊",
    "nice to meet you": "Nice to meet you too! 😊 I'm here to help with any questions you have. Feel free to ask me anything!",
    "ok": "Got it! Let me know if you need any help. 😊",
    "got it": "Great! Let me know if you have any other questions. 😊",
    "sure": "Sounds good! What can I help you with? 😊",
    "thanks a lot": "You're very welcome! 😊 Happy to help!",
    "thank you so much": "You're very welcome! 😊 Glad I could help!",
    "appreciate it": "Happy to help! 😊 Let me know if you need anything else.",
    "i'm good": "Glad to hear that! 😊 How can I help you today?",
    "i am good": "Glad to hear that! 😊 How can I help you today?",
    "i'm doing well": "That's great to hear! 😊 What can I do for you?",
    "i am doing well": "That's great to hear! 😊 What can I do for you?",
    "doing well": "Great to hear! 😊 How can I help you today?",
    "doing great": "Awesome! 😊 What can I assist you with?",
    "not bad": "Good to hear! 😊 How can I help you today?",
}




def classify_intent(message):
    """
    Classify a user message into GENERAL_CONVERSATION or DOCUMENT_QUERY.

    Uses a two-stage approach:
    1. Fast rule-based pre-filter for obvious social chat
    2. LLM-based classifier for everything else

    Returns:
        tuple: (intent_string, response_string_or_None)
    """
    text = message.strip()

    # Guard against empty input
    if not text:
        return INTENT_GENERAL_CONVERSATION, "Hello! 😊 How can I help you today?"

    # Stage 1: Rule-based pre-filter for obvious social chat
    if _is_social_chat(text):
        logger.info(f"Rule matched: GENERAL_CONVERSATION for '{text[:60]}'")

        # Generate a friendly response
        lower = text.lower().strip(" \t.,!?")

        # Exact match in template responses
        if lower in SOCIAL_RESPONSES:
            return INTENT_GENERAL_CONVERSATION, SOCIAL_RESPONSES[lower]

        # Fallback friendly response
        return INTENT_GENERAL_CONVERSATION, "Hello! 😊 How can I help you today?"

    # Stage 2: LLM-based classifier for non-obvious messages
    return _classify_with_llm(message)
