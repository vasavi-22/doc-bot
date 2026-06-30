from flask import Blueprint, request, jsonify, g
from middleware.auth_middleware import jwt_required
from services.conversation_service import (
    new_chat,
    list_chats,
    get_chat,
    rename_chat,
    remove_chat,
    add_user_message,
    add_assistant_message,
    get_chat_history,
)
from database import get_document_stats, get_chat_stats, get_recent_chats
from utils.logger import logger

conversations_bp = Blueprint("conversations", __name__, url_prefix="/api/conversations")


@conversations_bp.route("", methods=["GET"])
@jwt_required
def get_conversations():
    """List all conversations for the authenticated user."""
    try:
        chats = list_chats(g.user_id)
        return jsonify({"conversations": chats}), 200
    except Exception as e:
        logger.error(f"List conversations failed: {str(e)}")
        return jsonify({"error": str(e)}), 500


@conversations_bp.route("", methods=["POST"])
@jwt_required
def create_conversation():
    """Create a new conversation."""
    try:
        data = request.get_json() or {}
        title = data.get("title", "New Chat")
        chat = new_chat(g.user_id, title)
        return jsonify({"conversation": chat}), 201
    except Exception as e:
        logger.error(f"Create conversation failed: {str(e)}")
        return jsonify({"error": str(e)}), 500


@conversations_bp.route("/<chat_id>", methods=["GET"])
@jwt_required
def get_conversation(chat_id):
    """Get a single conversation with its messages."""
    try:
        chat = get_chat(chat_id)
        if not chat:
            return jsonify({"error": "Conversation not found"}), 404
        if chat["user_id"] != g.user_id:
            return jsonify({"error": "Unauthorized"}), 403

        messages = get_chat_history(chat_id)
        return jsonify({"conversation": chat, "messages": messages}), 200
    except Exception as e:
        logger.error(f"Get conversation failed: {str(e)}")
        return jsonify({"error": str(e)}), 500


@conversations_bp.route("/<chat_id>", methods=["PATCH"])
@jwt_required
def update_conversation(chat_id):
    """Update conversation title."""
    try:
        chat = get_chat(chat_id)
        if not chat:
            return jsonify({"error": "Conversation not found"}), 404
        if chat["user_id"] != g.user_id:
            return jsonify({"error": "Unauthorized"}), 403

        data = request.get_json() or {}
        if "title" in data:
            rename_chat(chat_id, data["title"])
            return jsonify({"message": "Conversation updated"}), 200
        return jsonify({"error": "No fields to update"}), 400
    except Exception as e:
        logger.error(f"Update conversation failed: {str(e)}")
        return jsonify({"error": str(e)}), 500


@conversations_bp.route("/<chat_id>", methods=["DELETE"])
@jwt_required
def delete_conversation(chat_id):
    """Delete a conversation and all its messages."""
    try:
        chat = get_chat(chat_id)
        if not chat:
            return jsonify({"error": "Conversation not found"}), 404
        if chat["user_id"] != g.user_id:
            return jsonify({"error": "Unauthorized"}), 403

        remove_chat(chat_id)
        return jsonify({"message": "Conversation deleted"}), 200
    except Exception as e:
        logger.error(f"Delete conversation failed: {str(e)}")
        return jsonify({"error": str(e)}), 500


@conversations_bp.route("/<chat_id>/messages", methods=["GET"])
@jwt_required
def get_messages(chat_id):
    """Get messages for a conversation."""
    try:
        chat = get_chat(chat_id)
        if not chat:
            return jsonify({"error": "Conversation not found"}), 404
        if chat["user_id"] != g.user_id:
            return jsonify({"error": "Unauthorized"}), 403

        messages = get_chat_history(chat_id)
        return jsonify({"messages": messages}), 200
    except Exception as e:
        logger.error(f"Get messages failed: {str(e)}")
        return jsonify({"error": str(e)}), 500


@conversations_bp.route("/dashboard-stats", methods=["GET"])
@jwt_required
def dashboard_stats():
    """Get dashboard statistics for the authenticated user."""
    try:
        user_id = g.user_id
        doc_stats = get_document_stats(user_id)
        chat_stats = get_chat_stats(user_id)
        recent = get_recent_chats(user_id)

        return jsonify({
            "total_documents": doc_stats["total_documents"],
            "total_pages": doc_stats["total_pages"],
            "total_chats": chat_stats["total_chats"],
            "total_questions": chat_stats["total_questions"],
            "recent_chats": recent
        }), 200
    except Exception as e:
        logger.error(f"Dashboard stats failed: {str(e)}")
        return jsonify({"error": str(e)}), 500
