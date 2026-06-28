from flask import Blueprint, request, jsonify
from services.rag_pipeline import query_rag
from services.intent_classifier import classify_intent, INTENT_GENERAL_CONVERSATION
from utils.logger import logger

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