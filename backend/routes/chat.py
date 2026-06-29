from flask import Blueprint, request, jsonify, Response, stream_with_context
from services.rag_pipeline import query_rag, query_rag_stream
from services.intent_classifier import classify_intent, INTENT_GENERAL_CONVERSATION
from utils.logger import logger
import json

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()

        # Validate input
        if not data or "message" not in data:
            logger.info("Chat request received")
            return jsonify({"error": "Message is required"}), 400

        question = data["message"]

        # Step 1: Classify intent using Groq LLM classifer
        # Returns (intent, conversational_response_if_general)
        intent, conversational_response = classify_intent(question)
        logger.info(f"Intent classified: {intent} for message: {question[:60]}")

        # Step 2: Handle general conversation — no RAG, no Pinecone retrieval
        if intent == INTENT_GENERAL_CONVERSATION:
            return jsonify({
                "answer": conversational_response,
                "sources": []
            })

        # Step 3: Document query — execute the RAG pipeline
        document_id = data.get("document_id")
        category = data.get("category")
        owner = data.get("owner")

        answer = query_rag(question=question, document_id=document_id, category=category, owner=owner)

        return jsonify(answer)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@chat_bp.route("/chat/stream", methods=["POST"])
def chat_stream():
    """SSE streaming endpoint for chat responses."""
    try:
        data = request.get_json()

        if not data or "message" not in data:
            return jsonify({"error": "Message is required"}), 400

        question = data["message"]
        document_id = data.get("document_id")
        category = data.get("category")
        owner = data.get("owner")

        # Classify intent
        intent, conversational_response = classify_intent(question)
        logger.info(f"Stream - Intent classified: {intent} for message: {question[:60]}")

        def generate():
            if intent == INTENT_GENERAL_CONVERSATION:
                # Stream the conversational response word by word
                if conversational_response:
                    words = conversational_response.split(" ")
                    for i, word in enumerate(words):
                        prefix = " " if i > 0 else ""
                        yield f"data: {json.dumps({'type': 'token', 'content': prefix + word})}\n\n"
                    yield f"data: {json.dumps({'type': 'sources', 'sources': []})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'sources', 'sources': []})}\n\n"
            else:
                # Stream the RAG response from Groq
                yield from query_rag_stream(
                    question=question,
                    document_id=document_id,
                    category=category,
                    owner=owner
                )

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