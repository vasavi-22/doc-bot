import uuid
from datetime import datetime, timezone
import json

from database import (
    create_chat,
    get_chats_by_user,
    get_chat_by_id,
    update_chat_title,
    update_chat_summary,
    delete_chat,
    touch_chat,
    save_message,
    get_messages_by_chat,
    get_message_count,
)
from utils.logger import logger

# How many recent messages to keep in full when a summary exists
RECENT_MESSAGES_TO_KEEP = 6

# Total messages before summarization is triggered
SUMMARIZATION_THRESHOLD = 12


def new_chat(user_id, title="New Chat"):
    """Create a new chat for the user."""
    chat_id = str(uuid.uuid4())
    create_chat(chat_id, user_id, title)
    logger.info(f"Created new chat {chat_id} for user {user_id}")
    return {"id": chat_id, "title": title}


def list_chats(user_id):
    """List all chats for a user, ordered by most recent first."""
    return get_chats_by_user(user_id)


def get_chat(chat_id):
    """Get a single chat by ID."""
    return get_chat_by_id(chat_id)


def rename_chat(chat_id, title):
    """Rename a chat."""
    update_chat_title(chat_id, title)


def remove_chat(chat_id):
    """Delete a chat and all its messages."""
    delete_chat(chat_id)


def _maybe_summarize(chat_id):
    """Check if summarization should run, and if so, generate/update the summary.

    Runs when total messages exceed SUMMARIZATION_THRESHOLD.
    Summarizes messages that fall outside the RECENT_MESSAGES_TO_KEEP window.
    """
    try:
        total = get_message_count(chat_id)
        if total < SUMMARIZATION_THRESHOLD:
            return

        from services.summarizer import generate_summary

        chat = get_chat_by_id(chat_id)
        existing_summary = chat.get("summary", "") if chat else ""

        # Get messages to summarize: all messages except the last RECENT_MESSAGES_TO_KEEP
        # We load all messages and slice from the front
        all_messages = get_messages_by_chat(chat_id, limit=total)
        messages_to_summarize = all_messages[:-RECENT_MESSAGES_TO_KEEP] if len(all_messages) > RECENT_MESSAGES_TO_KEEP else []

        if not messages_to_summarize:
            return

        logger.info(f"Summarizing {len(messages_to_summarize)} messages for chat {chat_id}")
        new_summary = generate_summary(messages_to_summarize, existing_summary)
        if new_summary:
            update_chat_summary(chat_id, new_summary)
            logger.info(f"Updated summary for chat {chat_id}")
    except Exception as e:
        logger.error(f"Failed to summarize chat {chat_id}: {e}")


def add_user_message(chat_id, content):
    """Save a user message and return it with its ID."""
    msg_id = str(uuid.uuid4())
    save_message(msg_id, chat_id, "user", content)
    touch_chat(chat_id)
    # Non-blocking summarization check
    _maybe_summarize(chat_id)
    return {"id": msg_id, "role": "user", "content": content}


def add_assistant_message(chat_id, content, sources=None):
    """Save an assistant message (with optional JSON sources) and return it."""
    msg_id = str(uuid.uuid4())
    sources_json = json.dumps(sources) if sources else None
    save_message(msg_id, chat_id, "assistant", content, sources_json)
    touch_chat(chat_id)
    # Non-blocking summarization check
    _maybe_summarize(chat_id)
    return {"id": msg_id, "role": "assistant", "content": content, "sources": sources or []}


def get_chat_history(chat_id, max_messages=RECENT_MESSAGES_TO_KEEP):
    """Get the last N messages for a chat as a list of dicts.

    Used by the conversational RAG pipeline to build LangChain
    message history.
    """
    messages = get_messages_by_chat(chat_id, limit=max_messages)
    return messages


def build_langchain_history(chat_id, max_messages=RECENT_MESSAGES_TO_KEEP):
    """Build a list of LangChain message objects from chat history.

    If a conversation summary exists, it's included as a SystemMessage
    at the start, followed by the most recent messages.

    This reduces token usage for long conversations while preserving
    conversational context.
    """
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

    lc_messages = []

    # Include conversation summary if it exists
    chat = get_chat_by_id(chat_id)
    if chat and chat.get("summary"):
        lc_messages.append(SystemMessage(
            content=f"The following is a summary of the earlier part of the conversation:\n\n{chat['summary']}"
        ))

    # Add recent messages
    messages = get_messages_by_chat(chat_id, limit=max_messages)
    for msg in messages:
        if msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            lc_messages.append(AIMessage(content=msg["content"]))

    return lc_messages
