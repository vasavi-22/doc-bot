from flask import Blueprint, request, jsonify, Response, stream_with_context, g
from services.intent_classifier import classify_intent, INTENT_GENERAL_CONVERSATION
from services.conversation_service import add_user_message, add_assistant_message, new_chat, get_chat
from services.conversational_rag import query_conversational_rag, query_conversational_rag_stream
from utils.logger import logger
from middleware.auth_middleware import jwt_required
from database import update_chat_title
import json
import re

chat_bp = Blueprint("chat", __name__)


def _auto_title_chat(chat_id, first_message):
    """Auto-generate a title from the first user message if chat is still titled 'New Chat'."""
    try:
        chat = get_chat(chat_id)
        if chat and chat.get("title") == "New Chat":
            # Derive title from the message
            clean = re.sub(r'\s+', ' ', first_message).strip()
            title = (clean[:47] + "...") if len(clean) > 50 else clean
            update_chat_title(chat_id, title)
            logger.info(f"Auto-titled chat {chat_id}: {title}")
    except Exception as e:
        logger.warning(f"Failed to auto-title chat {chat_id}: {e}")


@chat_bp.route("/chat", methods=["POST"])
@jwt_required
def chat():
    """Non-streaming chat endpoint with conversational memory."""
    try:
        data = request.get_json()

        if not data or "message" not in data:
            return jsonify({"error": "Message is required"}), 400

        question = data["message"]
        chat_id = data.get("chat_id")
        document_id = data.get("document_id")
        category = data.get("category")
        owner = data.get("owner")

        # If no chat_id provided, create a new chat
        if not chat_id:
            chat = new_chat(g.user_id)
            chat_id = chat["id"]

        # Auto-title the chat on first message
        _auto_title_chat(chat_id, question)

        # Save user message
        add_user_message(chat_id, question)

        # Step 1: Classify intent
        intent, conversational_response = classify_intent(question)
        logger.info(f"Intent classified: {intent} for message: {question[:60]}")

        # Step 2: Handle general conversation
        if intent == INTENT_GENERAL_CONVERSATION:
            add_assistant_message(chat_id, conversational_response, [])
            return jsonify({
                "answer": conversational_response,
                "sources": [],
                "chat_id": chat_id
            })

        # Step 3: Conversational RAG query
        answer = query_conversational_rag(
            question=question,
            chat_id=chat_id,
            document_id=document_id,
            category=category,
            owner=owner,
            user_id=g.user_id
        )

        if "error" not in answer:
            add_assistant_message(chat_id, answer.get("answer", ""), answer.get("sources", []))
            answer["chat_id"] = chat_id

        return jsonify(answer)

    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/chat/stream", methods=["POST"])
@jwt_required
def chat_stream():
    """SSE streaming endpoint with conversational memory."""
    try:
        data = request.get_json()

        if not data or "message" not in data:
            return jsonify({"error": "Message is required"}), 400

        question = data["message"]
        chat_id = data.get("chat_id")
        document_id = data.get("document_id")
        category = data.get("category")
        owner = data.get("owner")

        # If no chat_id provided, create a new chat
        if not chat_id:
            chat = new_chat(g.user_id)
            chat_id = chat["id"]

        # Auto-title the chat on first message (BEFORE saving user message)
        _auto_title_chat(chat_id, question)

        # Save user message
        add_user_message(chat_id, question)

        # Classify intent
        intent, conversational_response = classify_intent(question)
        logger.info(f"Stream - Intent classified: {intent} for message: {question[:60]}")

        def generate():
            if intent == INTENT_GENERAL_CONVERSATION:
                full_response = conversational_response or ""
                if full_response:
                    words = full_response.split(" ")
                    for i, word in enumerate(words):
                        prefix = " " if i > 0 else ""
                        yield f"data: {json.dumps({'type': 'token', 'content': prefix + word})}\n\n"
                yield f"data: {json.dumps({'type': 'sources', 'sources': []})}\n\n"
                yield f"data: {json.dumps({'type': 'chat_id', 'chat_id': chat_id})}\n\n"
                if full_response:
                    add_assistant_message(chat_id, full_response, [])
            else:
                full_answer = ""
                final_sources = []

                for event in query_conversational_rag_stream(
                    question=question,
                    chat_id=chat_id,
                    document_id=document_id,
                    category=category,
                    owner=owner,
                    user_id=g.user_id
                ):
                    try:
                        data_str = event[6:] if event.startswith("data: ") else event
                        parsed = json.loads(data_str)
                        if parsed.get("type") == "token":
                            full_answer += parsed.get("content", "")
                        elif parsed.get("type") == "sources":
                            final_sources = parsed.get("sources", [])
                    except (json.JSONDecodeError, IndexError):
                        pass
                    yield event

                if full_answer:
                    add_assistant_message(chat_id, full_answer, final_sources)

                yield f"data: {json.dumps({'type': 'chat_id', 'chat_id': chat_id})}\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive"
            }
        )

    except Exception as e:
        logger.error(f"Stream endpoint error: {str(e)}")
        return jsonify({"error": str(e)}), 500