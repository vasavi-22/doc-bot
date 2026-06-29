from services.llm import get_groq_llm_non_streaming
from utils.logger import logger

SUMMARIZATION_PROMPT = """\
You are a conversation summarizer. Your job is to produce a concise summary of the \
conversation so far. This summary will be used later as context for an AI assistant \
to answer follow-up questions.

Rules:
- Keep the summary to 3-5 sentences maximum.
- Capture the key topics, questions asked, and answers given.
- Preserve any specific terminology, document names, or technical details mentioned.
- Write in third person narrative style.
- Focus on what the user asked and what information was provided.
- If this is an update to an existing summary, incorporate the new messages into \
the existing summary naturally.

Existing summary (may be empty if this is the first summarization):
{existing_summary}

New messages to incorporate:
{messages_text}

Generate the updated summary (3-5 sentences):"""


def generate_summary(messages, existing_summary=""):
    """Generate or update a conversation summary using Groq.

    Args:
        messages: List of message dicts with 'role' and 'content' keys
        existing_summary: The current summary string (may be empty)

    Returns:
        str: The new/updated summary, or empty string on failure
    """
    if not messages:
        return existing_summary

    try:
        # Format messages as readable text
        lines = []
        for msg in messages:
            role_label = "User" if msg.get("role") == "user" else "Assistant"
            content = msg.get("content", "")
            # Truncate very long messages to save tokens
            if len(content) > 500:
                content = content[:500] + "..."
            lines.append(f"{role_label}: {content}")

        messages_text = "\n\n".join(lines)

        llm = get_groq_llm_non_streaming(
            model="llama-3.1-8b-instant",  # Faster, cheaper model for summarization
            temperature=0.2
        )

        prompt_text = SUMMARIZATION_PROMPT.format(
            existing_summary=existing_summary or "(none - this is the first summary)",
            messages_text=messages_text
        )

        result = llm.invoke(prompt_text)
        summary = result.content.strip()

        logger.info(f"Generated conversation summary ({len(summary)} chars)")
        return summary

    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        return existing_summary
